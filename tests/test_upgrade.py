"""These tests never contact Notion or require integration credentials."""

from copy import deepcopy

import pytest

from app.notion.client import NotionError
from app.notion.discovery import Inventory
from app.services.backup import backup
from app.services.state import load_manifest, read_tree
from app.services.upgrade import apply_plan
from app.services.validation import build_plan
from app.templates.catalog import EXPECTED_DATABASES, SPECS
from app.templates.dashboard import content_hash


class FakeNotion:
    def __init__(self):
        self.sources = {}
        self.pages = {}
        self.databases = {}
        self.blocks = {}
        self.children_by_id = {}
        self.records = {}
        self.writes = []
        self.fail_after_append = False
        self.counter = 0
        self.inventory = Inventory(api_version="2026-03-11", parent={"id": "parent"})
        for key, spec in SPECS.items():
            self.pages[key] = {"id": key}
            entry = {
                "status": "found",
                "page": self.pages[key],
                "blocks": [],
                "databases": [],
                "expected_title": spec.title,
            }
            self.inventory.templates[key] = entry
            self.children_by_id[key] = []
            for i, name in enumerate(EXPECTED_DATABASES[key]):
                source_id = f"ds-{key}-{i}"
                database_id = f"db-{key}-{i}"
                properties = {"Name": {"type": "title", "title": {}}}
                for formula in spec.formulas.get(name, []):
                    for prop, kind in formula.requires.items():
                        if prop not in spec.properties.get(name, {}):
                            properties[prop] = {"type": kind, kind: {}}
                source = {"id": source_id, "properties": properties}
                meta = {
                    "id": database_id,
                    "title": [{"text": {"content": name}}],
                    "data_sources": [{"id": source_id}],
                }
                self.sources[source_id] = source
                self.databases[database_id] = meta
                entry["databases"].append({"metadata": meta, "data_sources": [source]})
                db_block = {"id": database_id, "type": "child_database", "child_database": {}}
                self.children_by_id[key].append(db_block)
                record_id = f"record-{source_id}"
                self.records[source_id] = [{"id": record_id, "properties": {"Value": 42}}]
                self.pages[record_id] = self.records[source_id][0]
                self.children_by_id[record_id] = []

    def get(self, path):
        category, key = path.split("/", 1)
        return {
            "pages": self.pages,
            "data_sources": self.sources,
            "databases": self.databases,
            "blocks": self.blocks,
        }[category][key]

    def children(self, block_id):
        yield from deepcopy(self.children_by_id.get(block_id, []))

    def query(self, source_id):
        yield from deepcopy(self.records[source_id])

    def store_block(self, incoming):
        block = deepcopy(incoming)
        self.counter += 1
        block["id"] = f"block-{self.counter}"
        kind = block["type"]
        children = block[kind].pop("children", [])
        self.children_by_id[block["id"]] = [self.store_block(b) for b in children]
        block["has_children"] = bool(children)
        self.blocks[block["id"]] = block
        return block

    def send(self, method, path, payload):
        assert method == "PATCH"
        self.writes.append((path, deepcopy(payload)))
        if path.startswith("data_sources/"):
            source_id = path.split("/")[1]
            for name, schema in payload["properties"].items():
                assert name not in self.sources[source_id]["properties"]
                self.sources[source_id]["properties"][name] = {"type": next(iter(schema)), **schema}
            return self.sources[source_id]
        page_id = path.split("/")[1]
        roots = [self.store_block(b) for b in payload["children"]]
        self.children_by_id[page_id].extend(roots)
        if self.fail_after_append:
            self.fail_after_append = False
            raise NotionError("Request interrupted; outcome unknown.")
        return {"results": roots}


def empty_manifest():
    return {"version": 1, "dashboards": {}, "operations": []}


def test_all_upgrades_preserve_records_and_are_idempotent(tmp_path):
    client = FakeNotion()
    records_before = deepcopy(client.records)
    old_blocks = deepcopy(client.children_by_id)
    keys = list(SPECS)
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, keys, manifest)
    assert not plan["issues"]
    assert len(plan["operations"]) == 20
    assert not client.writes
    path, snapshot = backup(client, client.inventory, keys, tmp_path / "backups")
    assert len(snapshot["data_sources"]) == 22
    results = apply_plan(client, plan, manifest, path, tmp_path / "manifest.json")
    assert len(results) == 20
    assert client.records == records_before
    for key in keys:
        assert client.children_by_id[key][:-1] == old_blocks[key]
    repeat = build_plan(client, client.inventory, keys, manifest)
    assert not repeat["operations"]
    assert not repeat["issues"]


def test_missing_formula_input_blocks_apply(tmp_path):
    client = FakeNotion()
    source = client.sources["ds-finance-3"]
    source["properties"]["Amount"] = {"type": "rich_text", "rich_text": {}}
    plan = build_plan(client, client.inventory, ["finance"], empty_manifest())
    assert any("incompatible formula inputs" in issue for issue in plan["issues"])
    with pytest.raises(ValueError, match="conflicts"):
        apply_plan(client, plan, empty_manifest(), tmp_path / "absent")
    assert not client.writes


def test_unknown_append_is_reconciled_without_duplicate(tmp_path):
    client = FakeNotion()
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, ["creator"], manifest)
    path, _ = backup(client, client.inventory, ["creator"], tmp_path)
    client.fail_after_append = True
    manifest_path = tmp_path / "manifest.json"
    with pytest.raises(NotionError):
        apply_plan(client, plan, manifest, path, manifest_path)
    loaded = load_manifest(manifest_path)
    assert loaded["dashboards"]["creator"]["status"] == "pending"
    retry = build_plan(client, client.inventory, ["creator"], loaded)
    assert [op["kind"] for op in retry["operations"]] == ["reconcile"]
    write_count = len(client.writes)
    apply_plan(client, retry, loaded, path, manifest_path)
    assert len(client.writes) == write_count
    assert not build_plan(client, client.inventory, ["creator"], loaded)["operations"]


def test_edited_managed_content_is_preserved(tmp_path):
    client = FakeNotion()
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, ["habits"], manifest)
    path, _ = backup(client, client.inventory, ["habits"], tmp_path)
    apply_plan(client, plan, manifest, path, tmp_path / "manifest.json")
    root_id = manifest["dashboards"]["habits"]["block_id"]
    child = client.children_by_id[root_id][0]
    child["callout"]["rich_text"][0]["text"]["content"] = "My custom wording"
    repeat = build_plan(client, client.inventory, ["habits"], manifest)
    assert any("edited" in issue for issue in repeat["issues"])
    root = client.blocks[root_id]
    assert content_hash(read_tree(client, root)) != manifest["dashboards"]["habits"]["hash"]


def test_schema_race_stops_before_write(tmp_path):
    client = FakeNotion()
    plan = build_plan(client, client.inventory, ["finance"], empty_manifest())
    path, _ = backup(client, client.inventory, ["finance"], tmp_path)
    client.sources[plan["operations"][0]["target"]]["properties"]["User added"] = {"type": "number"}
    with pytest.raises(ValueError, match="changed since planning"):
        apply_plan(client, plan, empty_manifest(), path, tmp_path / "manifest.json")
    assert not client.writes


def test_missing_database_and_manifest_loss_are_conflicts(tmp_path):
    client = FakeNotion()
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, ["student"], manifest)
    path, _ = backup(client, client.inventory, ["student"], tmp_path)
    apply_plan(client, plan, manifest, path, tmp_path / "manifest.json")
    lost = build_plan(client, client.inventory, ["student"], empty_manifest())
    assert any("ownership manifest" in issue for issue in lost["issues"])
    client.inventory.templates["student"]["databases"].pop()
    missing = build_plan(client, client.inventory, ["student"], manifest)
    assert any("expected one database" in issue for issue in missing["issues"])


def test_backup_required_before_writes(tmp_path):
    client = FakeNotion()
    plan = build_plan(client, client.inventory, ["finance"], empty_manifest())
    with pytest.raises(ValueError, match="backup"):
        apply_plan(client, plan, empty_manifest(), tmp_path / "missing.json")
    assert not client.writes


def test_cli_upgrade_defaults_to_dry_run(monkeypatch, tmp_path):
    import importlib

    from typer.testing import CliRunner

    cli = importlib.import_module("app.main")
    client = FakeNotion()
    client.close = lambda: None
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, ["creator"], manifest)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "connect_upgrade", lambda: (None, client))
    monkeypatch.setattr(cli, "prepare", lambda *args: (client.inventory, manifest, plan))
    monkeypatch.setattr(
        cli, "create_backup", lambda *args: pytest.fail("Dry-run must not back up or apply")
    )
    result = CliRunner().invoke(cli.app, ["upgrade", "--template", "creator"])
    assert result.exit_code == 0, result.output
    assert "Dry-run only" in result.output
    assert not client.writes
    assert not (tmp_path / "state/manifest.json").exists()


def test_cli_backup_failure_prevents_all_writes(monkeypatch, tmp_path):
    import importlib

    from typer.testing import CliRunner

    cli = importlib.import_module("app.main")
    client = FakeNotion()
    client.close = lambda: None
    manifest = empty_manifest()
    plan = build_plan(client, client.inventory, ["finance"], manifest)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "connect_upgrade", lambda: (None, client))
    monkeypatch.setattr(cli, "prepare", lambda *args: (client.inventory, manifest, plan))

    def fail_backup(*args):
        raise NotionError("Notion HTTP 403; check access.")

    monkeypatch.setattr(cli, "create_backup", fail_backup)
    result = CliRunner().invoke(cli.app, ["upgrade", "--template", "finance", "--apply", "--yes"])
    assert result.exit_code == 1
    assert not client.writes
    assert not (tmp_path / "state/upgrade.lock").exists()


def test_audit_detects_record_changes():
    from app.services.audit import audit

    client = FakeNotion()
    snapshot = {
        "inventory": client.inventory.model_dump(),
        "data_sources": {
            key: {"schema": deepcopy(value), "records": deepcopy(client.records[key])}
            for key, value in client.sources.items()
        },
    }
    assert audit(client, snapshot, client.inventory)["passed"]
    first_source = next(iter(client.records))
    client.records[first_source][0]["properties"]["Value"] = 99
    result = audit(client, snapshot, client.inventory)
    assert not result["passed"]
    assert any("record property changed" in issue for issue in result["issues"])


def test_audit_allowed_help_edits_do_not_hide_deletion():
    from app.services.audit import audit
    from app.templates.dashboard import block

    client = FakeNotion()
    original = {"id": "owned-help", **block("paragraph", "Old help")}
    client.inventory.templates["finance"]["blocks"] = [original]
    snapshot = {
        "inventory": client.inventory.model_dump(),
        "data_sources": {
            key: {"schema": deepcopy(value), "records": deepcopy(client.records[key])}
            for key, value in client.sources.items()
        },
    }
    changed = {"id": "owned-help", **block("paragraph", "Updated help")}
    client.inventory.templates["finance"]["blocks"] = [changed]
    assert not audit(client, snapshot, client.inventory)["passed"]
    assert audit(client, snapshot, client.inventory, allowed_block_edits={"owned-help"})["passed"]
    client.inventory.templates["finance"]["blocks"] = []
    assert not audit(client, snapshot, client.inventory, allowed_block_edits={"owned-help"})[
        "passed"
    ]

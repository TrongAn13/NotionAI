"""Apply the premium redesign using journaled, additive operations."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.notion.client import NotionError
from app.premium.catalog import BRANDS, FIELDS, FORMULAS, RELATIONS, ROLLUPS
from app.premium.migration import budget_updates, only_empty, relation_updates
from app.premium.playbooks import HUBS, PLAYBOOKS, hub_relation, record_blocks
from app.premium.views import DASHBOARDS, compile_view
from app.services.state import digest, read_tree, save_json, signature
from app.templates.dashboard import block, rich, title

STATE_PATH = Path("state/premium-v2.json")


class PremiumUpgrade:
    def __init__(self, client, snapshot, backup_path, state_path=STATE_PATH):
        self.client = client
        self.snapshot = snapshot
        self.backup_path = Path(backup_path)
        if not self.backup_path.is_file():
            raise ValueError("A completed backup is required.")
        self.state_path = Path(state_path)
        self.state = (
            json.loads(self.state_path.read_text(encoding="utf-8"))
            if self.state_path.exists()
            else {
                "version": 2,
                "backup": str(backup_path),
                "operations": {},
                "templates": {},
                "linked_databases": [],
                "issues": [],
                "assets": {},
            }
        )
        if self.state.get("version") != 2:
            raise ValueError("Unsupported premium manifest version.")
        if self.state["backup"] != str(backup_path):
            raise ValueError("Preserve the original premium backup for recovery.")
        self.tables = {}
        self.records = {}
        for key, entry in snapshot["inventory"]["templates"].items():
            self.tables[key] = {}
            self.records[key] = {}
            for database in entry["databases"]:
                name = title(database["metadata"])
                if name in self.tables[key] or len(database["data_sources"]) != 1:
                    raise ValueError("Ambiguous source inventory.")
                source = database["data_sources"][0]
                self.tables[key][name] = deepcopy(source)
                self.records[key][name] = snapshot["data_sources"][source["id"]]["records"]
        self.save()

    def save(self):
        save_json(self.state_path, self.state)

    def operation(self, key, request, function, recover=None):
        previous = self.state["operations"].get(key)
        if previous and previous["status"] == "done":
            return previous["result"]
        if previous and previous["status"] == "unknown":
            recovered = recover() if recover else None
            if recovered is None:
                raise ValueError(f"Unresolved operation outcome: {key}; do not retry blindly.")
            previous.update(status="done", result=recovered)
            self.save()
            return recovered
        entry = {
            "status": "unknown",
            "started_at": datetime.now(UTC).isoformat(),
            "request_hash": digest(request),
            "request": request,
        }
        self.state["operations"][key] = entry
        self.save()
        try:
            result = function()
        except NotionError as exc:
            # An explicit rejected 4xx has no mutation. Timeouts/5xx remain unknown.
            entry["error"] = str(exc)
            if any(f"HTTP {status}" in str(exc) for status in (400, 401, 403, 404, 409, 422, 429)):
                entry["status"] = "rejected"
            self.save()
            raise
        entry.update(status="done", result=result)
        self.save()
        return result

    def refresh(self, key, table):
        source_id = self.tables[key][table]["id"]
        source = self.client.get(f"data_sources/{source_id}")
        if source.get("in_trash") or source.get("archived"):
            raise ValueError("Source is unavailable.")
        self.tables[key][table] = source
        return source

    def ensure_fields(self, key, table, desired, stage):
        if not desired:
            return
        current = self.refresh(key, table)
        missing = {}
        for name, spec in desired.items():
            kind = next(iter(spec))
            if name in current["properties"]:
                actual = current["properties"][name]
                if actual.get("type") != kind:
                    raise ValueError(f"Property type conflict: {key}/{table}/{name}")
                if (
                    kind == "formula"
                    and actual.get("formula", {}).get("expression") != spec[kind]["expression"]
                ):
                    raise ValueError(f"Formula conflict: {key}/{table}/{name}")
                if (
                    kind == "relation"
                    and actual["relation"]["data_source_id"] != spec[kind]["data_source_id"]
                ):
                    raise ValueError(f"Relation target conflict: {key}/{table}/{name}")
            else:
                missing[name] = spec
        op_id = f"schema:{key}:{table}:{stage}"
        if not missing:
            if self.state["operations"].get(op_id, {}).get("status") == "unknown":
                self.state["operations"][op_id].update(status="done", result={"reconciled": True})
                self.save()
            return
        if self.state["operations"].get(op_id, {}).get("status") == "done":
            raise ValueError(f"Managed field removed after upgrade: {key}/{table}/{stage}")
        self.operation(
            op_id,
            {"properties": missing},
            lambda: self.client.mutate(
                "PATCH", f"data_sources/{current['id']}", {"properties": missing}
            ),
        )
        self.refresh(key, table)

    def schemas(self):
        for key, tables in FIELDS.items():
            for table, fields in tables.items():
                self.ensure_fields(key, table, fields, "inputs")
            print(f"{key}: input fields ready", flush=True)
        for key, relations in RELATIONS.items():
            for table, name, target, inverse, _ in relations:
                source = self.refresh(key, table)
                destination = self.refresh(key, target)
                if name not in source["properties"] and inverse in destination["properties"]:
                    raise ValueError(f"Inverse field already exists: {key}/{target}/{inverse}")
                self.ensure_fields(
                    key,
                    table,
                    {
                        name: {
                            "relation": {
                                "data_source_id": destination["id"],
                                "type": "dual_property",
                                "dual_property": {"synced_property_name": inverse},
                            }
                        }
                    },
                    "relation-" + name,
                )
                self.refresh(key, target)
            print(f"{key}: connected database relations ready", flush=True)
        for key, tables in FORMULAS.items():
            for table, expressions in tables.items():
                for name, (relation, target_property, function) in (
                    ROLLUPS.get(key, {}).get(table, {}).items()
                ):
                    self.ensure_fields(
                        key,
                        table,
                        {
                            name: {
                                "rollup": {
                                    "relation_property_name": relation,
                                    "rollup_property_name": target_property,
                                    "function": function,
                                }
                            }
                        },
                        "rollup-" + name,
                    )
                # Formula dependencies are deliberately ordered; each preceding formula is
                # accepted before any dependent formula is submitted in the same source.
                for name, expression in expressions.items():
                    self.ensure_fields(
                        key, table, {name: {"formula": {"expression": expression}}}, name
                    )
            print(f"{key}: live calculations ready", flush=True)

    def migrate(self):
        updates = {}
        for key, relations in RELATIONS.items():
            for table, name, target, _, legacy in relations:
                if not legacy:
                    continue
                desired, skipped = relation_updates(
                    self.records[key][table], self.records[key][target], name, legacy
                )
                for record_id, values in desired.items():
                    updates.setdefault(record_id, {}).update(values)
                if skipped:
                    item = f"{key}/{table}/{name}: {skipped} legacy labels require manual matching"
                    if item not in self.state["issues"]:
                        self.state["issues"].append(item)
        for record_id, values in budget_updates(
            self.records["finance"]["Transactions"], self.records["finance"]["Monthly Budgets"]
        ).items():
            updates.setdefault(record_id, {}).update(values)
        for record in self.records["habits"]["Habit Log"]:
            if record["properties"].get("Completed", {}).get("checkbox"):
                updates.setdefault(record["id"], {})["Completion Mode"] = {
                    "select": {"name": "Full"}
                }
        for record_id, desired in updates.items():
            current = self.client.get(f"pages/{record_id}")
            missing = only_empty(current, desired)
            if missing:
                op_id = f"migrate:{record_id}"

                def recover(record_id=record_id, desired=desired):
                    live = self.client.get(f"pages/{record_id}")
                    return {"reconciled": True} if not only_empty(live, desired) else None

                self.operation(
                    op_id,
                    {"properties": missing},
                    lambda record_id=record_id, missing=missing: self.client.mutate(
                        "PATCH", f"pages/{record_id}", {"properties": missing}
                    ),
                    recover,
                )
        self.save()
        print(
            f"Existing records linked conservatively: {len(updates)} candidate records", flush=True
        )

    def banners(self):
        for key in BRANDS:
            path = Path("assets/banners") / f"{key}-v2.png"
            upload_id = self.operation(
                f"asset:{key}",
                {"file_hash": digest(path.read_bytes().hex())},
                lambda path=path: {"id": self.client.upload(path)},
            )["id"]
            self.state["assets"][key] = {"path": str(path), "file_upload_id": upload_id}
            page_id = self.snapshot["inventory"]["templates"][key]["page"]["id"]
            self.client.get(f"pages/{page_id}")
            payload = {
                "cover": {"type": "file_upload", "file_upload": {"id": upload_id}},
                "icon": {"type": "emoji", "emoji": BRANDS[key][2]},
            }
            self.operation(
                f"page-cover:{key}",
                payload,
                lambda page_id=page_id, payload=payload: self.client.mutate(
                    "PATCH", f"pages/{page_id}", payload
                ),
            )
            for records in self.records[key].values():
                for record in records:
                    current = self.client.get(f"pages/{record['id']}")
                    if not current.get("cover"):
                        cover = {"cover": payload["cover"]}
                        self.operation(
                            f"record-cover:{record['id']}",
                            cover,
                            lambda record=record, cover=cover: self.client.mutate(
                                "PATCH", f"pages/{record['id']}", cover
                            ),
                        )
            self.save()
            print(f"{key}: generated banner installed", flush=True)

    def append_owned(self, key, page_id, blocks, marker, position):
        def select(roots):
            matches = []
            for index in range(len(roots) - len(blocks) + 1):
                group = roots[index : index + len(blocks)]
                if not any(marker in json.dumps(b) for b in group):
                    continue
                actual = [signature(read_tree(self.client, b)) for b in group]
                if actual == [signature(b) for b in blocks]:
                    matches.append(group)
            return matches[0] if len(matches) == 1 else None

        def recover():
            roots = list(self.client.children(page_id))
            found = select(roots)
            return {"results": found} if found else None

        result = self.operation(
            key,
            {"children": blocks, "position": position},
            lambda: self.client.mutate(
                "PATCH", f"blocks/{page_id}/children", {"children": blocks, "position": position}
            ),
            recover,
        )
        selected = select(result.get("results", []))
        if selected is None:
            raise ValueError("Unexpected append response; preserve state and reconcile.")
        return selected

    def header(self, key):
        page_id = self.snapshot["inventory"]["templates"][key]["page"]["id"]
        name, tagline, emoji, color = BRANDS[key]
        marker = (
            "https://www.notion.so/"
            + page_id.replace("-", "")
            + "#"
            + uuid5(NAMESPACE_URL, page_id + "premium-v2").hex
        )
        introduction = block("paragraph", tagline)
        introduction["paragraph"]["rich_text"] += [rich("  Edition 2.0", marker, color="gray")]
        blocks = [
            block("heading_1", name),
            introduction,
            block(
                "callout",
                "Open Overview for your daily workspace. Use the tabs to capture, plan and review with the same connected data.",
                icon={"type": "emoji", "emoji": emoji},
                color=color + "_background",
            ),
            block("divider"),
        ]
        roots = self.append_owned(f"header:{key}", page_id, blocks, marker, {"type": "start"})
        return roots[-1]["id"]

    def create_view(self, op_key, payload):
        def recover():
            database_id = payload.get("database_id")
            if payload.get("view_id"):
                database_id = self.client.get(f"views/{payload['view_id']}")["parent"][
                    "database_id"
                ]
            if not database_id:
                # Lost linked-container response: find a unique view in newly added blocks only.
                page_id = payload["create_database"]["parent"]["page_id"]
                original = {b["id"] for b in self.snapshot["block_children"].get(page_id, [])}
                candidates = []
                for child in self.client.children(page_id):
                    if child["type"] != "child_database" or child["id"] in original:
                        continue
                    for ref in self.client.list_views(child["id"]):
                        candidate = self.client.get(f"views/{ref['id']}")
                        if (
                            candidate.get("name") == payload["name"]
                            and candidate.get("type") == payload["type"]
                        ):
                            candidates.append(candidate)
                return candidates[0] if len(candidates) == 1 else None
            candidates = []
            for ref in self.client.list_views(database_id):
                candidate = self.client.get(f"views/{ref['id']}")
                if (
                    candidate.get("name") == payload["name"]
                    and candidate.get("data_source_id") == payload["data_source_id"]
                ):
                    candidates.append(candidate)
            return candidates[0] if len(candidates) == 1 else None

        result = self.operation(
            op_key, payload, lambda: self.client.mutate("POST", "views", payload), recover
        )
        view_id = result["id"]
        current = self.client.get(f"views/{view_id}")
        if current.get("type") != payload["type"] or current.get("name") != payload["name"]:
            raise ValueError("Managed view identity changed; preserve and review.")
        if (
            payload["type"] != "dashboard"
            and current.get("data_source_id") != payload["data_source_id"]
        ):
            raise ValueError("View is scoped to a different source.")
        if "create_database" in payload:
            database_id = current["parent"]["database_id"]
            if database_id not in self.state["linked_databases"]:
                self.state["linked_databases"].append(database_id)
                self.save()
        return current

    def dashboards(self):
        for key, spec in DASHBOARDS.items():
            name, _, _, color = BRANDS[key]
            page_id = self.snapshot["inventory"]["templates"][key]["page"]["id"]
            anchor = self.header(key)
            source = self.tables[key][spec["primary"]]
            root = self.create_view(
                f"dashboard:{key}",
                {
                    "name": "Overview",
                    "type": "dashboard",
                    "data_source_id": source["id"],
                    "create_database": {
                        "parent": {"type": "page_id", "page_id": page_id},
                        "position": {"type": "after_block", "block_id": anchor},
                        "show_data_source_title": False,
                    },
                },
            )
            root_id = root["id"]
            database_id = root["parent"]["database_id"]
            self.state["templates"][key] = {
                "page_id": page_id,
                "brand": name,
                "dashboard_id": root_id,
                "linked_database_id": database_id,
            }
            self.save()
            for group_index, group in enumerate(spec["groups"]):
                row_views = []
                for widget_index, widget in enumerate(group):
                    op_key = f"widget:{key}:{group_index}:{widget_index}"
                    if self.state["operations"].get(op_key, {}).get("status") == "unavailable":
                        continue
                    payload = compile_view(widget, self.tables[key][widget["db"]], color)
                    payload["view_id"] = root_id
                    layout = self.client.get(f"views/{root_id}").get("configuration") or {}
                    rows = layout.get("rows", [])
                    row_index = next(
                        (
                            i
                            for i, row in enumerate(rows)
                            if any(w.get("view_id") in row_views for w in row.get("widgets", []))
                        ),
                        None,
                    )
                    payload["placement"] = (
                        {"type": "new_row"}
                        if row_index is None
                        else {"type": "existing_row", "row_index": row_index}
                    )
                    try:
                        created = self.create_view(op_key, payload)
                        row_views.append(created["id"])
                    except NotionError as exc:
                        if widget.get("optional") and (
                            "HTTP 400" in str(exc) or "HTTP 403" in str(exc)
                        ):
                            self.state["operations"][op_key]["status"] = "unavailable"
                            self.state["issues"].append(
                                f"Optional chart {key}/{widget['name']}: {exc}"
                            )
                            self.save()
                        else:
                            raise
            for i, tab in enumerate(spec["tabs"]):
                payload = compile_view(tab, self.tables[key][tab["db"]], color)
                payload["database_id"] = database_id
                self.create_view(f"tab:{key}:{i}", payload)
            print(f"{key}: native dashboard, widgets and working tabs installed", flush=True)

    def verify(self):
        counts = {"views": 0, "widgets": 0, "dashboards": 0, "covers": 0}
        for op_key, operation in self.state["operations"].items():
            if operation["status"] == "done" and op_key.startswith(
                ("dashboard:", "widget:", "tab:", "hub-view:")
            ):
                result = operation["result"]
                current = self.client.get(f"views/{result['id']}")
                if current.get("name") != result.get("name") or current.get("type") != result.get(
                    "type"
                ):
                    raise ValueError("A managed view was edited or removed.")
                counts["views"] += 1
                counts["widgets"] += op_key.startswith("widget:")
                counts["dashboards"] += op_key.startswith("dashboard:")
            if op_key.startswith("page-cover:") and operation["status"] == "done":
                key = op_key.split(":")[1]
                page_id = self.snapshot["inventory"]["templates"][key]["page"]["id"]
                current = self.client.get(f"pages/{page_id}")
                if not current.get("cover"):
                    raise ValueError("A generated page cover is missing.")
                counts["covers"] += 1
        return counts

    def workspaces(self):
        for key, tables in PLAYBOOKS.items():
            for table in tables:
                for record in self.records[key][table]:
                    record_id = record["id"]
                    op_key = f"workspace:{record_id}"
                    previous = self.state["operations"].get(op_key)
                    if not previous and list(self.client.children(record_id)):
                        self.state["issues"].append(
                            f"Preserved existing page body: {key}/{table}/{record_id}"
                        )
                        continue
                    marker, children = record_blocks(key, table, record_id)
                    # One container gives an unambiguous recovery boundary.
                    root = block(
                        "callout",
                        "Working space",
                        children=children,
                        icon={"type": "emoji", "emoji": BRANDS[key][2]},
                    )
                    root["callout"]["rich_text"] = [rich("Working space", marker)]
                    result = self.append_owned(op_key, record_id, [root], marker, {"type": "start"})
                    anchor = result[0]["id"]
                    for i, spec in enumerate(HUBS.get((key, table), [])):
                        payload = compile_view(spec, self.tables[key][spec["db"]], BRANDS[key][3])
                        payload["filter"] = {
                            "property": hub_relation(key, table),
                            "relation": {"contains": record_id},
                        }
                        payload["create_database"] = {
                            "parent": {"type": "page_id", "page_id": record_id},
                            "position": {"type": "after_block", "block_id": anchor},
                            "show_data_source_title": False,
                        }
                        linked = self.create_view(f"hub-view:{record_id}:{i}", payload)
                        anchor = linked["parent"]["database_id"]
            print(f"{key}: existing record workspaces connected", flush=True)

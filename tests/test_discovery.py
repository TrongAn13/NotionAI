from uuid import UUID

import httpx
import pytest
from typer.testing import CliRunner

from app.config import Settings
from app.main import app
from app.notion.client import NotionClient, NotionError
from app.notion.discovery import discover

PARENT = "401de7f2-96f6-80c9-9145-c4077252d990"


def client(handler, sleeps=None):
    return NotionClient(
        Settings(token="test-only", parent_page_id=UUID(PARENT)),
        transport=httpx.MockTransport(handler),
        sleep=(sleeps.append if sleeps is not None else lambda _: None),
    )


def response(data, status=200, headers=None):
    return httpx.Response(status, json=data, headers=headers)


def test_pagination_and_get_only():
    requests = []

    def handler(req):
        requests.append(req)
        if "start_cursor" not in req.url.params:
            return response({"results": [{"id": "one"}], "has_more": True, "next_cursor": "cursor"})
        assert req.url.params["start_cursor"] == "cursor"
        return response({"results": [{"id": "two"}], "has_more": False})

    c = client(handler)
    assert [b["id"] for b in c.children(PARENT)] == ["one", "two"]
    assert all(r.method == "GET" for r in requests)
    c.close()


def test_retry_after():
    sleeps = []
    calls = []

    def handler(req):
        calls.append(req)
        if len(calls) == 1:
            return response({}, 429, {"Retry-After": "7"})
        return response({"id": PARENT})

    c = client(handler, sleeps)
    assert c.get(f"pages/{PARENT}")["id"] == PARENT
    assert 7 in sleeps
    c.close()


@pytest.mark.parametrize("status", [401, 403, 404])
def test_permission_errors_do_not_leak_body(status):
    c = client(lambda _: response({"secret": "must-not-appear"}, status))
    inventory = discover(c, PARENT)
    assert not inventory.complete
    assert str(status) in inventory.issues[0]
    assert "must-not-appear" not in str(inventory)
    c.close()


def test_discovery_schema_nested_blocks_and_repeatability():
    def handler(req):
        path = req.url.path.removeprefix("/v1/")
        objects = {
            f"pages/{PARENT}": {"id": PARENT},
            f"blocks/{PARENT}/children": {
                "results": [
                    {
                        "id": "finance",
                        "type": "child_page",
                        "child_page": {"title": "Personal Finance Tracker"},
                    }
                ]
            },
            "pages/finance": {
                "id": "finance",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Personal Finance Tracker"}],
                    }
                },
            },
            "blocks/finance/children": {
                "results": [{"id": "column", "type": "column", "has_children": True}]
            },
            "blocks/column/children": {"results": [{"id": "db", "type": "child_database"}]},
            "databases/db": {"id": "db", "data_sources": [{"id": "ds"}]},
            "data_sources/ds": {"id": "ds", "properties": {"Amount": {"type": "number"}}},
        }
        assert req.method == "GET"
        return response(objects[path])

    c = client(handler)
    first = discover(c, PARENT)
    second = discover(c, PARENT)
    assert first.templates == second.templates
    finance = first.templates["finance"]
    assert finance["status"] == "found"
    assert finance["databases"][0]["data_sources"][0]["properties"]["Amount"]["type"] == "number"
    assert first.templates["creator"]["status"] == "missing"
    c.close()


def test_duplicate_titles_are_conflicts():
    def handler(req):
        if "/children" not in req.url.path:
            return response({"id": PARENT})
        return response(
            {
                "results": [
                    {"id": str(i), "type": "child_page", "child_page": {"title": "Student Planner"}}
                    for i in range(2)
                ]
            }
        )

    c = client(handler)
    inventory = discover(c, PARENT)
    assert inventory.templates["student"]["status"] == "conflict"
    c.close()


def test_repeated_cursor_stops():
    c = client(lambda _: response({"results": [], "has_more": True, "next_cursor": "same"}))
    with pytest.raises(NotionError, match="cursor"):
        list(c.children(PARENT))
    c.close()


def test_cli_requires_config_without_token_leak(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NOTION_API_TOKEN", raising=False)
    result = CliRunner().invoke(app, ["discover"])
    assert result.exit_code == 1
    assert "Configuration invalid" in result.output


def test_partial_failure_preserves_other_findings():
    def handler(req):
        path = req.url.path
        if path.endswith(f"pages/{PARENT}"):
            return response({"id": PARENT})
        if path.endswith(f"blocks/{PARENT}/children"):
            return response(
                {
                    "results": [
                        {
                            "id": "finance",
                            "type": "child_page",
                            "child_page": {"title": "Personal Finance Tracker"},
                        }
                    ]
                }
            )
        if path.endswith("pages/finance"):
            return response(
                {
                    "id": "finance",
                    "properties": {
                        "title": {
                            "type": "title",
                            "title": [{"plain_text": "Personal Finance Tracker"}],
                        }
                    },
                }
            )
        if path.endswith("blocks/finance/children"):
            return response({"results": [{"id": "db", "type": "child_database"}]})
        return response({}, 403)

    c = client(handler)
    inventory = discover(c, PARENT)
    assert inventory.templates["finance"]["status"] == "partial"
    assert inventory.templates["finance"]["page"]["id"] == "finance"
    assert not inventory.complete
    c.close()


def test_transport_retry_exhaustion():
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ReadTimeout("sensitive detail", request=req)

    c = client(handler)
    with pytest.raises(NotionError, match="connection failed"):
        c.get(f"pages/{PARENT}")
    assert len(calls) == 6
    c.close()


def test_complete_inventory_and_cli_reports(monkeypatch, tmp_path):
    from app.notion.discovery import TEMPLATES

    titles = {key: aliases[0] for key, aliases in TEMPLATES.items()}

    def handler(req):
        path = req.url.path.removeprefix("/v1/")
        if path == f"pages/{PARENT}":
            return response({"id": PARENT})
        if path == f"blocks/{PARENT}/children":
            return response(
                {
                    "results": [
                        {"id": key, "type": "child_page", "child_page": {"title": title}}
                        for key, title in titles.items()
                    ]
                }
            )
        if path.startswith("pages/"):
            key = path.split("/")[1]
            return response(
                {
                    "id": key,
                    "properties": {
                        "title": {"type": "title", "title": [{"plain_text": titles[key]}]}
                    },
                }
            )
        return response({"results": []})

    import importlib

    cli = importlib.import_module("app.main")
    c = client(handler)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NOTION_API_TOKEN", "test-only")
    monkeypatch.setenv("NOTION_PARENT_PAGE_ID", PARENT)
    monkeypatch.setattr(cli, "NotionClient", lambda _: c)
    result = CliRunner().invoke(app, ["discover"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "reports/inventory.json").exists()
    assert (tmp_path / "reports/inventory.md").exists()
    assert (tmp_path / "state/discovery.json").exists()
    assert '"complete": true' in (tmp_path / "reports/inventory.json").read_text()
    assert "test-only" not in (tmp_path / "reports/inventory.json").read_text()


def test_linked_database_is_not_discovered_as_duplicate():
    def handler(req):
        path = req.url.path.removeprefix("/v1/")
        data = {
            f"pages/{PARENT}": {"id": PARENT},
            f"blocks/{PARENT}/children": {
                "results": [
                    {
                        "id": "finance",
                        "type": "child_page",
                        "child_page": {"title": "Personal Finance Tracker"},
                    }
                ]
            },
            "pages/finance": {
                "id": "finance",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Personal Finance Tracker"}],
                    }
                },
            },
            "blocks/finance/children": {
                "results": [
                    {"id": dbid, "type": "child_database"} for dbid in ("original", "linked")
                ]
            },
            "databases/original": {"id": "original", "data_sources": [{"id": "source"}]},
            "databases/linked": {"id": "linked", "data_sources": [{"id": "source"}]},
            "data_sources/source": {
                "id": "source",
                "parent": {"type": "database_id", "database_id": "original"},
                "properties": {},
            },
        }
        return response(data[path])

    c = client(handler)
    inventory = discover(c, PARENT)
    entry = inventory.templates["finance"]
    assert len(entry["databases"]) == 1
    assert entry["databases"][0]["metadata"]["id"] == "original"
    assert entry["linked_databases"] == ["linked"]
    c.close()

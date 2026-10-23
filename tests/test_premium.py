"""Unit tests for premium migrations, native view configuration and durable replay."""

import json
import re
from copy import deepcopy

import pytest

from app.premium.catalog import BRANDS, FORMULAS, ROLLUPS
from app.premium.migration import (
    budget_updates,
    matching_id,
    only_empty,
    relation_updates,
    unique_index,
)
from app.premium.upgrade import PremiumUpgrade
from app.premium.views import DASHBOARDS, compile_view
from app.templates.dashboard import block


def record(record_id, name, **properties):
    return {
        "id": record_id,
        "properties": {
            "Name": {"type": "title", "title": [{"text": {"content": name}}]},
            **properties,
        },
    }


def test_ambiguous_names_are_not_linked():
    targets = [record("one", "Course A"), record("two", "course a")]
    assert matching_id(unique_index(targets), "Course A") is None
    source = [
        record(
            "task",
            "Essay",
            Course={"type": "rich_text", "rich_text": [{"text": {"content": "Course A"}}]},
        )
    ]
    changes, skipped = relation_updates(source, targets, "Course Link", "Course")
    assert not changes and skipped == 1


def test_unique_links_preserve_source_values():
    targets = [record("course", "Course A")]
    source = [
        record(
            "task",
            "Essay",
            Course={"type": "rich_text", "rich_text": [{"text": {"content": "Course A"}}]},
        )
    ]
    original = deepcopy(source)
    changes, skipped = relation_updates(source, targets, "Course Link", "Course")
    assert changes == {"task": {"Course Link": {"relation": [{"id": "course"}]}}}
    assert not skipped and source == original


def test_budget_match_requires_month_and_category():
    budgets = [
        record("food-oct", "2026-10", Category={"type": "select", "select": {"name": "Food"}}),
        record("food-nov", "2026-11", Category={"type": "select", "select": {"name": "Food"}}),
    ]
    transactions = [
        record(
            "grocery",
            "Groceries",
            Date={"type": "date", "date": {"start": "2026-10-03"}},
            Category={"type": "select", "select": {"name": "Food"}},
        )
    ]
    changes = budget_updates(transactions, budgets)
    assert changes["grocery"]["Budget Link"]["relation"] == [{"id": "food-oct"}]
    assert changes["food-oct"]["Month Start"]["date"]["start"] == "2026-10-01"


def test_migration_never_overwrites_existing_relation_or_zero():
    current = record(
        "record",
        "Name",
        Link={"type": "relation", "relation": [{"id": "chosen"}]},
        Amount={"type": "number", "number": 0},
    )
    assert not only_empty(
        current, {"Link": {"relation": [{"id": "other"}]}, "Amount": {"number": 100}}
    )
    with pytest.raises(ValueError):
        only_empty(current, {"Missing": {"number": 100}})


def test_view_compilation_uses_real_ids_and_preserves_visibility():
    schema = {
        "id": "source",
        "properties": {
            "Title": {"id": "title", "type": "title"},
            "Status": {"id": "status-id", "type": "select"},
            "Private": {"id": "private-id", "type": "rich_text"},
        },
    }
    spec = {
        "db": "Tasks",
        "name": "Work",
        "type": "board",
        "columns": ["Status"],
        "group": "Status",
    }
    payload = compile_view(spec, schema, "blue")
    assert payload["configuration"]["group_by"]["property_id"] == "status-id"
    assert {p["property_id"]: p["visible"] for p in payload["configuration"]["properties"]} == {
        "title": True,
        "status-id": True,
        "private-id": False,
    }
    assert "database_id" not in payload


def test_no_hardcoded_dates_in_view_filters():
    assert not re.search(r"20\d{2}-\d{2}-\d{2}", json.dumps(DASHBOARDS))
    assert all(spec["tabs"] and spec["groups"] for spec in DASHBOARDS.values())


def test_formula_expressions_are_balanced_and_empty_safe():
    for tables in FORMULAS.values():
        for formulas in tables.values():
            for name, expression in formulas.items():
                clean = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', expression)
                level = 0
                for character in clean:
                    level += (character == "(") - (character == ")")
                    assert level >= 0, name
                assert level == 0, name
    assert "Graded Weight" in FORMULAS["student"]["Assignments"]
    assert "Outstanding Balance" in FORMULAS["freelancer"]["Invoices"]
    assert "Minimum Days Last 7" in ROLLUPS["habits"]["Habits"]


def test_operation_journal_replays_without_duplicate_mutation(tmp_path):
    upgrade = PremiumUpgrade.__new__(PremiumUpgrade)
    upgrade.state_path = tmp_path / "state.json"
    upgrade.state = {"operations": {}}
    calls = []

    def mutate():
        calls.append(1)
        return {"id": "existing"}

    assert upgrade.operation("view", {"name": "A"}, mutate) == {"id": "existing"}
    assert upgrade.operation("view", {"name": "A"}, mutate) == {"id": "existing"}
    assert len(calls) == 1
    upgrade.state["operations"]["unknown"] = {"status": "unknown"}
    with pytest.raises(ValueError, match="Unresolved"):
        upgrade.operation("unknown", {}, mutate)
    assert len(calls) == 1
    assert upgrade.operation("unknown", {}, mutate, lambda: {"id": "recovered"}) == {
        "id": "recovered"
    }
    assert len(calls) == 1


def test_every_brand_has_a_distinct_original_banner():
    from pathlib import Path

    assert len(BRANDS) == 5
    assert all((Path("assets/banners") / f"{key}-v2.png").is_file() for key in BRANDS)


def test_append_response_can_include_existing_siblings(tmp_path):
    upgrade = PremiumUpgrade.__new__(PremiumUpgrade)
    upgrade.state_path = tmp_path / "state.json"
    marker = "https://example.com/owned-marker"
    new = block("paragraph", "New section")
    new["paragraph"]["rich_text"][0]["text"]["link"] = {"url": marker}
    created = {"id": "new", **deepcopy(new)}
    old = {"id": "old", **block("paragraph", "Keep existing user content")}
    upgrade.state = {
        "operations": {"append": {"status": "done", "result": {"results": [created, old]}}}
    }
    upgrade.client = object()
    result = upgrade.append_owned("append", "page", [new], marker, {"type": "start"})
    assert [b["id"] for b in result] == ["new"]
    assert upgrade.state["operations"]["append"]["result"]["results"][1] == old


def test_premium_transport_rejects_resource_recreation_and_trashing():
    from uuid import UUID

    import httpx

    from app.config import Settings
    from app.premium.client import PremiumClient

    client = PremiumClient(
        Settings(token="test-only", parent_page_id=UUID("401de7f296f680c99145c4077252d990")),
        transport=httpx.MockTransport(lambda _: pytest.fail("Must reject before HTTP")),
        sleep=lambda _: None,
    )
    for method, path, payload in [
        ("POST", "pages", {}),
        ("POST", "databases", {}),
        ("PATCH", "pages/page", {"erase_content": True}),
        ("PATCH", "blocks/block", {"in_trash": True}),
    ]:
        with pytest.raises(ValueError):
            client.mutate(method, path, payload)
    client.close()

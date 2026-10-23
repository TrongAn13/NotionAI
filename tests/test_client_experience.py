"""Client portal boundaries must not expose internal business sources."""

import json

import pytest

from app.premium.client_experience import (
    ACTIVITY,
    CONTENT,
    REVIEWS,
    ExperienceClient,
    portal_blocks,
)


def test_creation_rejects_unregistered_parent_before_network_access():
    client = ExperienceClient.__new__(ExperienceClient)
    client.creation_parents = {"owned-portal"}
    # No HTTP client: any accidental network access fails this test.
    for endpoint, parent in [
        ("pages", {"page_id": "other-client"}),
        ("databases", {"page_id": "internal-home"}),
        ("pages", {"data_source_id": "internal-projects"}),
        ("users", {"page_id": "owned-portal"}),
    ]:
        with pytest.raises(ValueError, match="outside"):
            client.create(endpoint, {"parent": parent})


def test_portal_sources_have_no_cross_client_relations_or_rollups():
    for fields in (CONTENT, REVIEWS, ACTIVITY):
        assert all(not ({"relation", "rollup"} & set(spec)) for spec in fields.values())
    body = json.dumps(portal_blocks(), ensure_ascii=False)
    assert "Northstar" not in body and "Mia" not in body
    assert "link_to_page" not in body and "synced_block" not in body


def test_example_is_labeled_as_fictional_and_keeps_manual_approval_boundary():
    body = json.dumps(portal_blocks(True), ensure_ascii=False)
    assert "FICTIONAL WALKTHROUGH" in body
    assert "not a verified signature" in body
    assert "does not authorize extra fees" in body

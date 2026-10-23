"""JSON snapshots of accessible resources; no automatic rollback is promised."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.services.state import save_json


def backup(client, inventory, keys, directory=Path("backups")):
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "inventory": inventory.model_dump(),
        "pages": {},
        "databases": {},
        "data_sources": {},
        "block_children": {},
        "limitations": [
            "JSON is not a native Notion backup; no automatic rollback.",
            "File URLs may expire; file bytes and comments are not downloaded.",
            "Record property values may be truncated by Notion's page response limits.",
        ],
    }
    visited = set()

    def page(page_id):
        if page_id in snapshot["pages"]:
            return
        snapshot["pages"][page_id] = client.get(f"pages/{page_id}")
        children(page_id)

    def database(database_id):
        if database_id in snapshot["databases"]:
            return
        meta = client.get(f"databases/{database_id}")
        snapshot["databases"][database_id] = meta
        for source in meta.get("data_sources", []):
            source_id = source["id"]
            schema = client.get(f"data_sources/{source_id}")
            records = list(client.query(source_id))
            snapshot["data_sources"][source_id] = {"schema": schema, "records": records}
            for record in records:
                page(record["id"])

    def children(block_id):
        if block_id in visited:
            return
        visited.add(block_id)
        blocks = list(client.children(block_id))
        snapshot["block_children"][block_id] = blocks
        for block in blocks:
            kind = block["type"]
            if kind == "child_database":
                database(block["id"])
            elif kind == "child_page":
                page(block["id"])
            elif block.get("has_children"):
                children(block["id"])

    for key in keys:
        entry = inventory.templates[key]
        if entry["status"] != "found":
            raise ValueError(f"Cannot back up unavailable template: {key}")
        page(entry["page"]["id"])
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = directory / f"snapshot-{stamp}-{uuid4().hex[:8]}.json"
    save_json(path, snapshot)
    return path, snapshot

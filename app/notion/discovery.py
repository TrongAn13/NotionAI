"""Discover resources afresh; cached IDs are never trusted for API requests."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.notion.client import NotionError

TEMPLATES = {
    "finance": ["Personal Finance Tracker"],
    "student": ["Student Planner"],
    "creator": ["Content Creator OS"],
    # The original builder derives this title from the ZIP directory.
    "habits": ["Habit & Productivity Tracker", "Habit Productivity Tracker"],
    "freelancer": ["Freelancer Business OS", "Client Desk"],
}


class Inventory(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    api_version: str
    parent: dict = Field(default_factory=dict)
    templates: dict = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    complete: bool = True
    managed_content_status: str = (
        "Discovery inventories content; use plan and the local manifest to verify managed upgrades."
    )


def normalize(title):
    return " ".join(title.casefold().split())


def page_title(page):
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(
                t.get("plain_text", t.get("text", {}).get("content", ""))
                for t in prop.get("title", [])
            )
    return ""


def discover(client, parent_id, api_version="2026-03-11"):
    inventory = Inventory(api_version=api_version)

    def issue(message):
        inventory.complete = False
        inventory.issues.append(message)

    def read(path):
        try:
            value = client.get(path)
            if value.get("in_trash") or value.get("archived"):
                issue(f"Unavailable archived resource: {path}")
                return None
            return value
        except NotionError as exc:
            issue(f"{path}: {exc}")
            return None

    visited = set()
    source_cache = {}

    def walk(block_id, output):
        if block_id in visited:
            return
        visited.add(block_id)
        try:
            for block in client.children(block_id):
                output.append(block)
                if block.get("has_children") and block.get("type") not in (
                    "child_page",
                    "child_database",
                ):
                    walk(block["id"], output)
        except NotionError as exc:
            issue(f"blocks/{block_id}: {exc}")

    inventory.parent = read(f"pages/{parent_id}") or {}
    if not inventory.parent:
        return inventory
    parent_blocks = []
    walk(parent_id, parent_blocks)
    for key, aliases in TEMPLATES.items():
        candidates = [
            b
            for b in parent_blocks
            if b.get("type") == "child_page"
            and normalize(b["child_page"].get("title", "")) in {normalize(a) for a in aliases}
        ]
        entry = {
            "expected_title": aliases[0],
            "status": "missing",
            "databases": [],
            "blocks": [],
            "candidate_ids": [b["id"] for b in candidates],
        }
        inventory.templates[key] = entry
        if len(candidates) != 1:
            entry["status"] = "conflict" if candidates else "missing"
            issue(f"{aliases[0]}: {entry['status']} ({len(candidates)} matches)")
            continue
        page = read(f"pages/{candidates[0]['id']}")
        if not page:
            entry["status"] = "inaccessible"
            continue
        if normalize(page_title(page)) not in {normalize(a) for a in aliases}:
            entry["status"] = "conflict"
            issue(f"{aliases[0]}: retrieved title differs from discovery")
            continue
        entry.update(status="found", page=page)
        issue_count = len(inventory.issues)
        walk(page["id"], entry["blocks"])
        for block in entry["blocks"]:
            if block.get("type") != "child_database":
                continue
            database = read(f"databases/{block['id']}")
            if not database:
                continue
            sources = []
            for source in database.get("data_sources", []):
                if source["id"] not in source_cache:
                    source_cache[source["id"]] = read(f"data_sources/{source['id']}")
                schema = source_cache[source["id"]]
                if schema:
                    owner = schema.get("parent", {}).get("database_id")
                    if owner and owner.replace("-", "") != database["id"].replace("-", ""):
                        # A linked view references an existing source owned by another
                        # container. Keep its page block, but do not discover it as a
                        # duplicate primary database or copy its underlying records.
                        continue
                    sources.append(schema)
            if (
                not sources
                and database.get("data_sources")
                and all(
                    source_cache.get(source["id"]) is not None
                    for source in database["data_sources"]
                )
            ):
                entry.setdefault("linked_databases", []).append(database["id"])
                continue
            entry["databases"].append({"metadata": database, "data_sources": sources})
        if len(inventory.issues) > issue_count:
            entry["status"] = "partial"
    return inventory


def markdown_report(inventory):
    lines = [
        "# Notion resource inventory",
        "",
        f"Generated: {inventory.generated_at}",
        f"API version: {inventory.api_version}",
        f"Complete: {inventory.complete}",
        "",
        "| Template | Status | Blocks | Databases | Data sources |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for entry in inventory.templates.values():
        sources = sum(len(d["data_sources"]) for d in entry["databases"])
        lines.append(
            f"| {entry['expected_title']} | {entry['status']} | "
            f"{len(entry['blocks'])} | {len(entry['databases'])} | {sources} |"
        )
    lines.extend(["", "## Issues", ""] + (inventory.issues or ["None."]))
    lines.extend(
        [
            "",
            "## Scope and limitations",
            "",
            "Read-only discovery; no records are queried or modified. This is not a backup.",
            (
                "Only child databases exposed in template block trees are inventoried. "
                "Linked database views and databases inside nested child pages are not followed."
            ),
            inventory.managed_content_status,
            "JSON contains accessible page metadata, blocks and data-source property schemas.",
        ]
    )
    return "\n".join(lines) + "\n"

"""Read-only comparison against the snapshot made before an upgrade."""


def audit(client, snapshot, after_inventory, *, allowed_block_edits=()):
    issues = []
    before_inventory = snapshot["inventory"]
    original_blocks = 0
    for key, before in before_inventory["templates"].items():
        if key not in after_inventory.templates:
            continue
        after = after_inventory.templates[key]
        if before.get("page", {}).get("id") != after.get("page", {}).get("id"):
            issues.append(f"{key}: template page ID changed")
        after_blocks = {b["id"]: b for b in after["blocks"]}
        for old in before["blocks"]:
            original_blocks += 1
            new = after_blocks.get(old["id"])
            if (
                not new
                or new.get("type") != old.get("type")
                or (
                    old["id"] not in allowed_block_edits
                    and new.get(old["type"]) != old.get(old["type"])
                )
            ):
                issues.append(f"{key}: original block changed or missing: {old['id']}")
    before_count = 0
    after_count = 0
    for source_id, old_source in snapshot["data_sources"].items():
        after_source = client.get(f"data_sources/{source_id}")
        for name, schema in old_source["schema"]["properties"].items():
            if after_source.get("properties", {}).get(name) != schema:
                issues.append(f"Original property schema changed: {source_id}/{name}")
        before_records = {r["id"]: r for r in old_source["records"]}
        after_records = {r["id"]: r for r in client.query(source_id)}
        before_count += len(before_records)
        after_count += len(after_records)
        if set(before_records) != set(after_records):
            issues.append(f"Record IDs changed in {source_id}")
        for record_id, old in before_records.items():
            new = after_records.get(record_id, {})
            for name, value in old.get("properties", {}).items():
                if new.get("properties", {}).get(name) != value:
                    issues.append(f"Original record property changed: {record_id}/{name}")
    return {
        "passed": not issues,
        "issues": issues,
        "records_before": before_count,
        "records_after": after_count,
        "original_blocks_checked": original_blocks,
        "data_sources_checked": len(snapshot["data_sources"]),
        "scope": "Accessible queried records and original template blocks/property schemas.",
    }

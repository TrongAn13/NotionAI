"""Apply a reviewed additive plan, journaling before ambiguous network operations."""

from datetime import UTC, datetime
from pathlib import Path

from app.notion.client import NotionError
from app.services.state import digest, read_tree, save_json
from app.services.validation import block_text
from app.templates.dashboard import content_hash


def apply_plan(client, plan, manifest, backup_path, manifest_path=Path("state/manifest.json")):
    if plan["issues"]:
        raise ValueError("Resolve all plan conflicts before applying any changes.")
    backup_path = Path(backup_path)
    if not backup_path.is_file():
        raise ValueError("A completed backup is required before applying changes.")
    results = []
    for operation in plan["operations"]:
        record = {
            "template": operation["template"],
            "kind": operation["kind"],
            "target": operation["target"],
            "status": "pending",
            "started_at": datetime.now(UTC).isoformat(),
            "backup": str(backup_path),
        }
        manifest["operations"].append(record)
        save_json(manifest_path, manifest)
        try:
            key = operation["template"]
            if operation["kind"] == "schema":
                current = client.get(f"data_sources/{operation['target']}")
                if digest(current["properties"]) != operation["before_hash"]:
                    raise ValueError("Data-source schema changed since planning; replan required.")
                if set(current["properties"]) & set(operation["properties"]):
                    raise ValueError("Refusing to overwrite an existing property.")
                client.send(
                    "PATCH",
                    f"data_sources/{operation['target']}",
                    {"properties": operation["properties"]},
                )
                updated = client.get(f"data_sources/{operation['target']}")
                for name, schema in operation["properties"].items():
                    expected_type = next(iter(schema))
                    if updated.get("properties", {}).get(name, {}).get("type") != expected_type:
                        raise ValueError("Schema write could not be verified; stop and replan.")
            elif operation["kind"] == "dashboard":
                page = client.get(f"pages/{operation['target']}")
                if page.get("in_trash") or page.get("archived"):
                    raise ValueError("Template was archived after planning.")
                roots = list(client.children(operation["target"]))
                if any("[NTB:" in block_text(b) for b in roots):
                    raise ValueError(
                        "Managed dashboard appeared after planning; refusing duplicate."
                    )
                manifest["dashboards"][key] = {
                    "page_id": operation["target"],
                    "marker": operation["marker"],
                    "hash": operation["hash"],
                    "version": plan["version"],
                    "status": "pending",
                }
                save_json(manifest_path, manifest)
                # Never retry append blindly. A lost response is reconciled using this marker.
                result = client.send(
                    "PATCH",
                    f"blocks/{operation['target']}/children",
                    {"children": [operation["block"]]},
                )
                if len(result.get("results", [])) != 1:
                    raise ValueError("Append outcome unknown; preserve manifest and reconcile.")
                created = result["results"][0]
                actual_hash = content_hash(read_tree(client, created))
                if actual_hash != operation["hash"]:
                    raise ValueError("Dashboard content could not be verified; reconcile required.")
                manifest["dashboards"][key].update(block_id=created["id"], status="done")
            elif operation["kind"] == "reconcile":
                root = client.get(f"blocks/{operation['target']}")
                if content_hash(read_tree(client, root)) != operation["hash"]:
                    raise ValueError("Managed content changed during reconciliation.")
                manifest["dashboards"][key].update(block_id=operation["target"], status="done")
            else:
                raise ValueError("Unknown operation kind.")
            record["status"] = "done"
            results.append(record.copy())
        except (NotionError, ValueError, OSError) as exc:
            record["status"] = "failed_or_unknown"
            record["error"] = str(exc)
            save_json(manifest_path, manifest)
            raise
        save_json(manifest_path, manifest)
    return results

"""Read-only upgrade planning and strict schema compatibility checks."""

from uuid import NAMESPACE_URL, uuid5

from app.notion.discovery import normalize
from app.services.state import digest, read_tree
from app.templates.catalog import EXPECTED_DATABASES, SPECS, VERSION
from app.templates.dashboard import content_hash, dashboard, title


def block_text(block):
    body = block.get(block.get("type"), {})
    return "".join(
        t.get("plain_text", t.get("text", {}).get("content", "")) for t in body.get("rich_text", [])
    )


def build_plan(client, inventory, keys, manifest):
    plan = {
        "version": VERSION,
        "templates": keys,
        "operations": [],
        "issues": [],
        "manual_setup": {key: SPECS[key].manual for key in keys},
    }
    for key in keys:
        spec = SPECS[key]
        entry = inventory.templates.get(key, {})
        if entry.get("status") != "found":
            plan["issues"].append(f"{key}: unavailable or ambiguous template; skipped")
            continue
        page_id = entry["page"]["id"]
        databases = {}
        for database in entry["databases"]:
            databases.setdefault(normalize(title(database["metadata"])), []).append(database)
        for expected in EXPECTED_DATABASES[key]:
            matches = databases.get(normalize(expected), [])
            if len(matches) != 1 or len(matches[0]["data_sources"]) != 1:
                plan["issues"].append(
                    f"{key}/{expected}: expected one database and one data source"
                )
                continue
            source = matches[0]["data_sources"][0]
            current = source.get("properties", {})
            available = dict(current)
            additions = {}
            for name, schema in spec.properties.get(expected, {}).items():
                kind = next(iter(schema))
                if name in current:
                    if current[name].get("type") != kind:
                        plan["issues"].append(
                            f"{key}/{expected}/{name}: incompatible existing type"
                        )
                else:
                    additions[name] = schema
                    available[name] = {"type": kind, **schema}
            for formula in spec.formulas.get(expected, []):
                if any(
                    available.get(name, {}).get("type") != kind
                    for name, kind in formula.requires.items()
                ):
                    plan["issues"].append(
                        f"{key}/{expected}/{formula.name}: incompatible formula inputs"
                    )
                    continue
                schema = {"formula": {"expression": formula.expression}}
                if formula.name in current:
                    existing = current[formula.name]
                    if (
                        existing.get("type") != "formula"
                        or existing.get("formula", {}).get("expression") != formula.expression
                    ):
                        plan["issues"].append(
                            f"{key}/{expected}/{formula.name}: existing formula differs"
                        )
                else:
                    additions[formula.name] = schema
            if additions:
                plan["operations"].append(
                    {
                        "kind": "schema",
                        "template": key,
                        "target": source["id"],
                        "database": expected,
                        "before_hash": digest(current),
                        "properties": additions,
                    }
                )
        managed = manifest["dashboards"].get(key)
        root_blocks = list(client.children(page_id))
        marker_blocks = [b for b in root_blocks if "[NTB:" in block_text(b)]
        if managed:
            if managed["page_id"] != page_id:
                plan["issues"].append(f"{key}: manifest belongs to a different page")
                continue
            candidates = [b for b in marker_blocks if f"[{managed['marker']}]" in block_text(b)]
            if len(candidates) != 1 or len(marker_blocks) != 1:
                plan["issues"].append(
                    f"{key}: managed root missing, duplicated or append outcome unresolved"
                )
                continue
            actual = candidates[0]
            if managed.get("block_id") and managed["block_id"] != actual["id"]:
                plan["issues"].append(f"{key}: managed block ID mismatch")
                continue
            actual_hash = content_hash(read_tree(client, actual))
            wanted = dashboard(spec, entry, managed["marker"])
            if actual_hash != managed["hash"] or content_hash(wanted) != managed["hash"]:
                plan["issues"].append(
                    f"{key}: managed content was edited or version changed; preserve and review"
                )
                continue
            if managed.get("status") == "pending":
                plan["operations"].append(
                    {
                        "kind": "reconcile",
                        "template": key,
                        "target": actual["id"],
                        "hash": actual_hash,
                    }
                )
        elif marker_blocks:
            plan["issues"].append(f"{key}: managed content exists without local ownership manifest")
        else:
            marker = f"NTB:{key}:{uuid5(NAMESPACE_URL, page_id + VERSION).hex}"
            root = dashboard(spec, entry, marker)
            plan["operations"].append(
                {
                    "kind": "dashboard",
                    "template": key,
                    "target": page_id,
                    "marker": marker,
                    "hash": content_hash(root),
                    "block": root,
                }
            )
    return plan


def plan_markdown(plan):
    lines = [
        "# Upgrade plan",
        "",
        f"Version: {plan['version']}",
        f"Operations: {len(plan['operations'])}",
        "",
    ]
    for operation in plan["operations"]:
        if operation["kind"] == "schema":
            lines.append(
                f"- {operation['template']}/{operation['database']}: add "
                + ", ".join(operation["properties"])
            )
        else:
            lines.append(f"- {operation['template']}: {operation['kind']} managed dashboard")
    lines += ["", "## Conflicts", ""] + (plan["issues"] or ["None."])
    lines += ["", "## Manual setup", ""]
    for key, items in plan["manual_setup"].items():
        lines += [f"### {SPECS[key].title}", ""] + [f"- {item}" for item in items] + [""]
    return "\n".join(lines) + "\n"

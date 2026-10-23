"""Update only the previously verified application-owned help blocks."""

from copy import deepcopy

from app.services.state import digest, load_manifest, read_tree, save_json, signature
from app.templates.catalog import SPECS
from app.templates.dashboard import rich

HELP = {
    "finance": [
        "Use Overview and This month to review recorded income and expenses. Link movements to the right account and monthly budget.",
        "Monthly budget desk calculates Linked Spending and Live Budget Left from linked transactions.",
        "Recorded Balance uses opening balance and linked movements. Match unresolved legacy account labels in Match your accounts.",
        "For transfers, select Movement Kind = Transfer and complete Account Link plus Transfer Destination. Check that the two accounts are different.",
        "Use one base currency for summed amounts. Saved Amount is the starting savings balance; enter only later additions in Goal Contribution to avoid double counting.",
    ],
    "student": [
        "Use Plan a study session to connect a course, date, topic, duration and the next review date.",
        "Assignment desk and Deadline calendar are configured. Link each task to its course and set the real deadline.",
        "Exam room is configured. Define Revision Focus and update Readiness after practice.",
        "Current Graded Average uses only graded assessments with valid points and weights. Course Completion uses related assignments; set Weekly Study Capacity to see workload signals.",
        "Use an existing example to learn the workflow. Adapt grade weights to your syllabus before relying on the calculation.",
    ],
    "creator": [
        "Production floor is configured with stage grouping, cover images and the next production action.",
        "Release calendar and Channel rooms are connected to the same underlying production data.",
        "Use Packaging lab before production and Learning log after release. Compare the same channel and measurement window.",
        "Engagement is (likes + comments) / views. CTR % is a separate metric entered from your platform; it is not inferred from engagement.",
        "Publishing and importing YouTube analytics remain manual unless a separate integration is configured.",
    ],
    "habits": [
        "Seven Day Rhythm compares full logged actions in the last seven days against Goal Per Week. It does not claim a daily streak.",
        "Full, Minimum, Skipped and Rest remain distinct. An unlogged day earns no credit; Rest is not a completed action.",
        "Use Minimum day plans to define a small alternative, a cue and the next restart action.",
        "Use Weekly reset for energy, friction and one adjustment; keep monthly reflections alongside the weekly reviews.",
        "Plan eligible habit opportunities deliberately. The system does not automatically create recurring daily records.",
    ],
    "freelancer": [
        "Client pipeline is configured. Record a real Next Follow Up date and contact leads manually.",
        "Your next deliveries and Delivery calendar are connected through Project Link.",
        "Payments requiring attention shows remaining balances. Amount Received supports partial payments; mark Payment Status = Paid only when fully paid.",
        "Recorded Receipts is cash recorded from invoices, not profit. Fee per Logged Hour is project fee divided by logged task hours.",
        "Use Scope guard to compare revision allowance with actual rounds and review change requests before accepting extra work.",
        "Client rooms and project workspaces are linked. Review unresolved legacy names instead of guessing matches.",
        "No invoices are sent and no clients are contacted automatically. Internal client pages are private; filtered views are not access control.",
    ],
}


def update_help(upgrade):
    client = upgrade.client
    manifest = load_manifest()
    for key, spec in SPECS.items():
        managed = manifest["dashboards"].get(key)
        if not managed:
            continue
        root = client.get(f"blocks/{managed['block_id']}")
        tree = read_tree(client, root)
        if digest(signature(tree)) != managed["hash"]:
            original_blocks = {
                b["id"]: b for blocks in upgrade.snapshot["block_children"].values() for b in blocks
            }

            def original_tree(block_id, original_blocks=original_blocks):
                value = deepcopy(original_blocks[block_id])
                if value.get("has_children"):
                    value[value["type"]]["children"] = [
                        original_tree(b["id"])
                        for b in upgrade.snapshot["block_children"].get(block_id, [])
                    ]
                return value

            expected = original_tree(managed["block_id"])
            for child in expected[expected["type"]].get("children", []):
                operation = upgrade.state["operations"].get(f"help:{key}:{child['id']}", {})
                if operation.get("status") in ("done", "unknown"):
                    kind = child["type"]
                    child[kind].update(operation["request"][kind])
            if digest(signature(tree)) != digest(signature(expected)):
                raise ValueError(f"Application help was edited: {key}; preserve and review.")
        replacements = dict(zip(spec.manual, HELP[key], strict=True))
        changed_ids = []
        for child in tree[root["type"]].get("children", []):
            kind = child["type"]
            body = child.get(kind, {})
            text = "".join(
                t.get("plain_text", t.get("text", {}).get("content", ""))
                for t in body.get("rich_text", [])
            )
            replacement = replacements.get(text)
            if text == "Setup checklist":
                replacement = "Using your connected workspace"
            elif text.startswith("Template guide v1.0.0"):
                replacement = "Template guide v2.0.0 • Native views, connected data and original banner artwork."
            if replacement is None:
                continue
            payload = {kind: {"rich_text": [rich(replacement)]}}

            def recover(child=child, payload=payload):
                live = client.get(f"blocks/{child['id']}")
                wanted = deepcopy(child)
                wanted[wanted["type"]].update(payload[wanted["type"]])
                return live if signature(live) == signature(wanted) else None

            upgrade.operation(
                f"help:{key}:{child['id']}",
                payload,
                lambda child=child, payload=payload: client.mutate(
                    "PATCH", f"blocks/{child['id']}", payload
                ),
                recover,
            )
            changed_ids.append(child["id"])
        refreshed = read_tree(client, client.get(f"blocks/{managed['block_id']}"))
        managed["hash"] = digest(signature(refreshed))
        managed["version"] = "2.0.0"
        save_json("state/manifest.json", manifest)
        edits = upgrade.state.setdefault("authorized_help_edits", {})
        edits[key] = sorted(set(edits.get(key, [])) | set(changed_ids))
        upgrade.save()
        print(f"{key}: managed help refreshed for v2", flush=True)

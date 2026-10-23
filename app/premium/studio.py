"""A usable design/web project workflow over Client Desk's existing sources."""

import json
from pathlib import Path

import typer

from app.config import Settings
from app.main import upgrade_lock
from app.premium.client import PremiumClient
from app.premium.studio_content import project_kit, to_html
from app.premium.upgrade import PremiumUpgrade
from app.premium.views import compile_view, view
from app.services.state import save_json, signature
from app.templates.dashboard import block, rich

STATE = Path("state/client-desk-studio.json")
INPUTS = {
    "Projects": {
        "Target Outcome": {"rich_text": {}},
        "Success Measure": {"rich_text": {}},
        "Approval Contact": {"rich_text": {}},
        "Client Assets Due": {"date": {}},
        "Client Assets Ready": {"checkbox": {}},
        "Scope Agreed": {"checkbox": {}},
        "Handoff Accepted": {"checkbox": {}},
        "Service Package": {
            "select": {
                "options": [
                    {"name": s} for s in ("Website", "Landing page", "Brand identity", "Retainer")
                ]
            }
        },
    },
    "Tasks": {
        "Work Type": {
            "select": {
                "options": [
                    {"name": "Delivery", "color": "blue"},
                    {"name": "Change request", "color": "orange"},
                ]
            }
        },
        "Decision": {
            "select": {
                "options": [
                    {"name": s}
                    for s in (
                        "Requested",
                        "Estimating",
                        "Awaiting approval",
                        "Approved",
                        "Declined",
                        "Deferred",
                    )
                ]
            }
        },
        "Request Summary": {"rich_text": {}},
        "Requested On": {"date": {}},
        "Extra Fee": {"number": {"format": "number"}},
        "Extra Hours": {"number": {"format": "number"}},
        "Deadline Impact Days": {"number": {"format": "number"}},
        "Estimate Reviewed": {"checkbox": {}},
        "Approval Evidence": {"url": {}},
        "Decision On": {"date": {}},
    },
}
TASK_FORMULAS = {
    "Change Gate": 'if(prop("Work Type") != "Change request", "", if(prop("Decision") == "Declined", "Declined", if(prop("Decision") == "Deferred", "Deferred", if(not prop("Estimate Reviewed"), "Estimate first", if(prop("Decision") != "Approved", "Awaiting approval", if(or(empty(prop("Approval Evidence")), empty(prop("Decision On"))), "Record approval", "Approved"))))))',
    "Approved Extra Fee": 'if(prop("Change Gate") == "Approved", max(0, prop("Extra Fee")), 0)',
    "Approved Extra Hours": 'if(prop("Change Gate") == "Approved", max(0, prop("Extra Hours")), 0)',
    "Needs Decision": 'if(and(prop("Work Type") == "Change request", and(prop("Change Gate") != "Approved", and(prop("Change Gate") != "Declined", prop("Change Gate") != "Deferred"))), 1, 0)',
    "Delivery Item": 'if(prop("Work Type") == "Change request", 0, 1)',
    "Open Delivery Item": 'if(and(prop("Delivery Item") == 1, prop("Remaining Task") == 1), 1, 0)',
}
ROLLUPS = {
    "Approved Extras": "Approved Extra Fee",
    "Approved Extra Hours": "Approved Extra Hours",
    "Pending Change Decisions": "Needs Decision",
    "Delivery Items": "Delivery Item",
    "Open Deliveries": "Open Delivery Item",
}
PROJECT_FORMULAS = {
    "Project Gate": 'if(empty(prop("Target Outcome")), "Define outcome", if(not prop("Scope Agreed"), "Confirm scope", if(not prop("Client Assets Ready"), "Waiting for assets", if(and(prop("Status") == "Completed", not prop("Handoff Accepted")), "Confirm handoff", "Ready to deliver"))))',
    "Delivery Completion": 'if(prop("Delivery Items") <= 0, "No delivery tasks", format(round(100 * (1 - prop("Open Deliveries") / prop("Delivery Items")))) + "% delivered")',
}


def load():
    pointer = json.loads(Path("state/client-desk-studio-backup.json").read_text(encoding="utf-8"))
    path = Path(pointer["path"])
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["inventory"]["templates"] = {
        "freelancer": snapshot["inventory"]["templates"]["freelancer"]
    }
    settings = Settings.load()
    client = PremiumClient(settings)
    page_id = snapshot["inventory"]["templates"]["freelancer"]["page"]["id"]
    page = client.get("pages/" + page_id)
    if page["parent"].get("page_id", "").replace("-", "") != settings.parent_page_id.hex:
        client.close()
        raise ValueError("Workspace parent changed")
    upgrade = PremiumUpgrade(client, snapshot, path, STATE)
    for table in upgrade.tables["freelancer"]:
        upgrade.refresh("freelancer", table)
    return client, upgrade, page_id


def add_schemas(upgrade):
    for table, fields in INPUTS.items():
        upgrade.ensure_fields("freelancer", table, fields, "studio-inputs")
    # Create formula dependencies in order; Notion may type-check each new
    # property before sibling formulas from the same patch become available.
    for name, expression in TASK_FORMULAS.items():
        upgrade.ensure_fields(
            "freelancer",
            "Tasks",
            {name: {"formula": {"expression": expression}}},
            "studio-formula-" + name,
        )
    upgrade.ensure_fields(
        "freelancer",
        "Projects",
        {
            name: {
                "rollup": {
                    "relation_property_name": "Task Entries",
                    "rollup_property_name": source,
                    "function": "sum",
                }
            }
            for name, source in ROLLUPS.items()
        },
        "studio-rollups",
    )
    upgrade.ensure_fields(
        "freelancer",
        "Projects",
        {k: {"formula": {"expression": v}} for k, v in PROJECT_FORMULAS.items()},
        "studio-project-formulas",
    )


def change_views(project_id=None):
    clauses = [{"property": "Work Type", "select": {"equals": "Change request"}}]
    if project_id:
        clauses.append({"property": "Project Link", "relation": {"contains": project_id}})
    return [
        view(
            "Tasks",
            "Capture request",
            columns=[
                "Task",
                "Project Link",
                "Request Summary",
                "Requested On",
                "Decision",
                "Change Gate",
            ],
            filter={"and": clauses},
        ),
        view(
            "Tasks",
            "Needs a decision",
            columns=[
                "Task",
                "Project Link",
                "Extra Fee",
                "Extra Hours",
                "Deadline Impact Days",
                "Decision",
                "Change Gate",
            ],
            filter={
                "and": clauses
                + [{"property": "Needs Decision", "formula": {"number": {"equals": 1}}}]
            },
        ),
        view(
            "Tasks",
            "Approved changes",
            columns=[
                "Task",
                "Project Link",
                "Approved Extra Fee",
                "Approved Extra Hours",
                "Deadline Impact Days",
                "Approval Evidence",
                "Decision On",
            ],
            filter={
                "and": clauses
                + [{"property": "Change Gate", "formula": {"string": {"equals": "Approved"}}}]
            },
        ),
        view(
            "Tasks",
            "Estimate & approval",
            columns=[
                "Task",
                "Project Link",
                "Extra Fee",
                "Extra Hours",
                "Deadline Impact Days",
                "Estimate Reviewed",
                "Decision",
                "Approval Evidence",
                "Decision On",
                "Change Gate",
            ],
            filter={"and": clauses},
        ),
    ]


def install_views(upgrade, page_id, anchor, key, specs):
    first = None
    for index, spec in enumerate(specs):
        payload = compile_view(spec, upgrade.tables["freelancer"][spec["db"]], "blue")
        if first is None:
            payload["create_database"] = {
                "parent": {"type": "page_id", "page_id": page_id},
                "position": {"type": "after_block", "block_id": anchor},
                "show_data_source_title": False,
            }
        else:
            payload["database_id"] = first["parent"]["database_id"]
        result = upgrade.create_view(f"studio:view:{key}:{index}", payload)
        if first is None:
            first = result
    return first


def apply_studio(upgrade, page_id):
    add_schemas(upgrade)
    foundation = json.loads(Path("state/client-desk-v3.json").read_text(encoding="utf-8"))
    modules = foundation["home_modules"]
    for module in modules.values():
        live = upgrade.client.get("views/" + module["view_id"])
        if live["parent"]["database_id"] != module["database_id"]:
            raise ValueError("Home view moved to another source container")
    marker = "https://www.notion.so/" + page_id.replace("-", "") + "#design-web-studio"
    projects = upgrade.records["freelancer"]["Projects"]
    if not projects:
        raise ValueError("No existing project available; no demo record is invented")
    for project in projects:
        project_marker = marker + "-" + project["id"].replace("-", "")
        reconcile_intro(upgrade, "studio:kit:" + project["id"], project_kit(project_marker)[0])
        roots = upgrade.append_owned(
            "studio:kit:" + project["id"],
            project["id"],
            project_kit(project_marker),
            project_marker,
            {"type": "start"},
        )
        label = block("heading_2", "Change desk · this project")
        label["heading_2"]["rich_text"].append(
            rich(" ↗", project_marker + "-changes", color="gray")
        )
        section = upgrade.append_owned(
            "studio:changes-label:" + project["id"],
            project["id"],
            [label],
            project_marker + "-changes",
            {"type": "after_block", "after_block": {"id": roots[3]["id"]}},
        )
        install_views(
            upgrade, project["id"], section[0]["id"], project["id"], change_views(project["id"])
        )
    label = block("heading_2", "Scope Guard  /  Change desk")
    label["heading_2"]["rich_text"].append(rich(" ↗", marker + "-desk", color="gray"))
    help_text = block(
        "paragraph",
        "Capture the request. Estimate the impact. Record approval before scheduling extra work.",
    )
    roots = upgrade.append_owned(
        "studio:home-changes",
        page_id,
        [label, help_text],
        marker + "-desk",
        {"type": "after_block", "after_block": {"id": modules["projects"]["database_id"]}},
    )
    change_root = install_views(upgrade, page_id, roots[1]["id"], "home", change_views())
    # Ready-to-run project intake, with only meaningful inputs visible.
    intake = view(
        "Projects",
        "Project intake",
        columns=[
            "Project",
            "Client Link",
            "Service Package",
            "Target Outcome",
            "Success Measure",
            "Approval Contact",
            "Scope Agreed",
            "Client Assets Due",
            "Client Assets Ready",
            "Project Gate",
        ],
    )
    payload = compile_view(intake, upgrade.tables["freelancer"]["Projects"], "blue")
    payload["database_id"] = modules["projects"]["database_id"]
    upgrade.create_view("studio:view:intake", payload)
    # Pending requests cannot silently appear as delivery work.
    focus_id = modules["focus"]["view_id"]
    patch = {
        "filter": {
            "and": [
                {"property": "Remaining Task", "formula": {"number": {"equals": 1}}},
                {"property": "Work Type", "select": {"does_not_equal": "Change request"}},
            ]
        }
    }
    upgrade.operation(
        "studio:focus-filter",
        patch,
        lambda: upgrade.client.mutate("PATCH", "views/" + focus_id, patch),
        lambda: (
            upgrade.client.get("views/" + focus_id)
            if upgrade.client.get("views/" + focus_id).get("filter") == patch["filter"]
            else None
        ),
    )
    gallery = view(
        "Projects",
        "Active projects",
        "gallery",
        [
            "Client Link",
            "Next Action",
            "Due Date",
            "Project Gate",
            "Delivery Completion",
            "Pending Change Decisions",
        ],
        filter={
            "and": [
                {"property": "Status", "select": {"does_not_equal": label}}
                for label in ("Completed", "Cancelled", "Archived")
            ]
        },
        sort="Due Date",
    )
    config = compile_view(gallery, upgrade.tables["freelancer"]["Projects"], "blue")[
        "configuration"
    ]
    patch = {"configuration": config}
    upgrade.operation(
        "studio:project-card",
        patch,
        lambda: upgrade.client.mutate("PATCH", "views/" + modules["projects"]["view_id"], patch),
    )
    # Short onboarding lives above the work modules, rather than a long guide wall.
    nav_results = foundation["operations"]["home:navigation"]["result"]["results"]
    nav_id = next(b["id"] for b in nav_results if b["type"] == "column_list")
    onboarding = block(
        "toggle",
        "Start your first design / web project",
        children=[
            block(
                "numbered_list_item",
                "Open the existing Website Refresh example to see the project kit. Its dates and amounts are fictional starter data.",
            ),
            block(
                "numbered_list_item",
                "Create your client in Client rooms. Open Project intake and create a project using the Design / Web project template; set Client Link and the outcome before agreeing scope.",
            ),
            block(
                "numbered_list_item",
                "Agree deliverables, revision allowance, fee and dates. Add Delivery tasks in All tasks, link the project and set a real due date.",
            ),
            block(
                "numbered_list_item",
                "Use Change desk for extra requests, Money desk for recorded invoices/payments, and the project handoff checklist before closing.",
            ),
            block(
                "paragraph",
                "Keep the master private. Share a reviewed handoff document with the client rather than the whole workspace. Email examples are editable drafts; nothing is sent automatically.",
            ),
        ],
    )
    onboarding["toggle"]["rich_text"].append(rich(" ↗", marker + "-start", color="gray"))
    upgrade.append_owned(
        "studio:onboarding",
        page_id,
        [onboarding],
        marker + "-start",
        {"type": "after_block", "after_block": {"id": nav_id}},
    )
    upgrade.state["change_home"] = change_root
    upgrade.save()
    folder = Path("product/client-desk")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project-template.html").write_text(to_html(project_kit("")), encoding="utf-8")
    save_json(folder / "project-template.blocks.json", project_kit(""))
    save_json(
        "reports/client-desk-studio-result.json",
        {
            "page_id": page_id,
            "backup": str(upgrade.backup_path),
            "project_kits": len(projects),
            "new_records": 0,
            "new_data_sources": 0,
            "native_database_template_verified": False,
        },
    )
    print("Studio kit, project intake and connected change desks installed.", flush=True)


def reconcile_intro(upgrade, key, desired):
    """Repair the one API-normalized zero-width marker without appending again."""
    op = upgrade.state["operations"].get(key)
    if not op or op["status"] != "done":
        return
    old = op["result"]["results"][0]
    if any(p.get("text", {}).get("link") for p in old["callout"]["rich_text"]):
        return
    actual = upgrade.client.get("blocks/" + old["id"])
    if signature(actual) != signature(old):
        raise ValueError("Project introduction was edited; retain it for review")
    payload = {"callout": desired["callout"]}
    result = upgrade.operation(
        "studio:marker-repair:" + old["id"],
        payload,
        lambda: upgrade.client.mutate("PATCH", "blocks/" + old["id"], payload),
    )
    op["result"]["results"][0] = result
    op["normalization_reconciled"] = (
        "Notion dropped zero-width link; linked the existing heading instead. No duplicate append."
    )
    upgrade.save()


def install_native_templates(upgrade):
    templates = json.loads(
        Path("state/client-desk-native-templates.json").read_text(encoding="utf-8")
    )
    for table, info in templates.items():
        if not info.get("ui_template_banner_verified"):
            raise ValueError("Native template must first be identified in Notion UI")
        page = upgrade.client.get("pages/" + info["id"])
        source = upgrade.tables["freelancer"][table]
        title = "".join(
            t.get("plain_text", "")
            for p in page["properties"].values()
            if p["type"] == "title"
            for t in p["title"]
        )
        if page["parent"].get("data_source_id") != source["id"] or title != info["title"]:
            raise ValueError("Native template identity changed")
        if info["id"] in {p["id"] for p in upgrade.client.query(source["id"])}:
            raise ValueError("A native template must not be a regular project/task record")
        marker = "https://www.notion.so/" + info["id"].replace("-", "") + "#studio-template"
        if table == "Projects":
            roots = upgrade.append_owned(
                "studio:native-kit:Projects",
                info["id"],
                project_kit(marker),
                marker,
                {"type": "start"},
            )
            label = block("heading_2", "Change desk · this project")
            label["heading_2"]["rich_text"].append(rich(" ↗", marker + "-changes", color="gray"))
            section = upgrade.append_owned(
                "studio:native-changes-label",
                info["id"],
                [label],
                marker + "-changes",
                {"type": "after_block", "after_block": {"id": roots[3]["id"]}},
            )
            install_views(
                upgrade, info["id"], section[0]["id"], "native-project", change_views(info["id"])
            )
            properties = {"Status": {"select": {"name": "Planned"}}}
        else:
            callout = block(
                "callout", icon={"type": "emoji", "emoji": "🧭"}, color="orange_background"
            )
            callout["callout"]["rich_text"] = [
                rich("CHANGE REQUEST", marker, bold=True),
                rich("\nEstimate → confirm → schedule"),
            ]
            content = [
                callout,
                block("heading_2", "Request brief"),
                block("paragraph", "Requested outcome: [what should change and why?]"),
                block(
                    "paragraph",
                    "Difference from agreed scope: [affected deliverable, quantity or acceptance check]",
                ),
                block(
                    "paragraph",
                    "Estimate assumptions: [dependencies, fee/currency, hours and proposed deadline effect]",
                ),
                block("heading_2", "Decision record"),
                block("paragraph", "Client response: [short summary and who confirmed it]"),
                block(
                    "paragraph",
                    "Use the properties for Decision, Decision On and Approval Evidence. Keep this row as history. Approved work becomes a separate Delivery task.",
                ),
                block(
                    "quote",
                    "Thanks for requesting [change]. It adds [deliverable] beyond [scope]. The proposed additional fee is [amount/currency], estimated effort [hours] and delivery impact [days/revised date]. Please confirm these details in writing before we schedule the work.",
                ),
            ]
            upgrade.append_owned(
                "studio:native-kit:Tasks", info["id"], content, marker, {"type": "start"}
            )
            properties = {
                "Work Type": {"select": {"name": "Change request"}},
                "Decision": {"select": {"name": "Requested"}},
            }
        payload = {"properties": properties}
        upgrade.operation(
            "studio:native-defaults:" + table,
            payload,
            lambda pid=info["id"], p=payload: upgrade.client.mutate("PATCH", "pages/" + pid, p),
        )
    upgrade.state["native_templates"] = templates
    upgrade.save()
    print("Two native database templates populated; no ordinary records created.", flush=True)


def polish_studio(upgrade, page_id):
    templates = upgrade.state["native_templates"]
    native_project = templates["Projects"]["id"]
    marker = "https://www.notion.so/" + native_project.replace("-", "") + "#studio-template"
    kit = upgrade.state["operations"]["studio:native-kit:Projects"]["result"]["results"]
    anchor = kit[6]["id"]
    for key, heading, spec in [
        (
            "deliveries",
            "Your deliveries",
            view(
                "Tasks",
                "Project deliveries",
                columns=["Task", "Due Date", "Priority", "Status", "Hours Logged"],
                filter={
                    "and": [
                        {"property": "Project Link", "relation": {"contains": native_project}},
                        {"property": "Work Type", "select": {"does_not_equal": "Change request"}},
                    ]
                },
                sort="Due Date",
            ),
        ),
        (
            "invoices",
            "Project invoices",
            view(
                "Invoices",
                "Project invoices",
                columns=["Invoice", "Amount", "Due Date", "Outstanding Balance", "Receipt State"],
                filter={"property": "Project Link", "relation": {"contains": native_project}},
                sort="Due Date",
            ),
        ),
    ]:
        label = block("heading_2", heading)
        label["heading_2"]["rich_text"].append(rich(" ↗", marker + "-" + key, color="gray"))
        roots = upgrade.append_owned(
            "studio:native-label:" + key,
            native_project,
            [label],
            marker + "-" + key,
            {"type": "after_block", "after_block": {"id": anchor}},
        )
        result = install_views(upgrade, native_project, roots[0]["id"], "native-" + key, [spec])
        anchor = result["parent"]["database_id"]
    # Existing project-local delivery/invoice views remain in place; improve
    # their visible ordering and keep request rows out of deliveries.
    for project in upgrade.records["freelancer"]["Projects"]:
        for b in upgrade.snapshot["block_children"].get(project["id"], []):
            if b["type"] != "child_database":
                continue
            for v in upgrade.snapshot.get("views", {}).get(b["id"], []):
                table = next(
                    (
                        name
                        for name in ("Tasks", "Invoices")
                        if v.get("data_source_id") == upgrade.tables["freelancer"][name]["id"]
                    ),
                    None,
                )
                if table is None:
                    continue
                fields = (
                    ["Task", "Due Date", "Priority", "Status", "Hours Logged"]
                    if table == "Tasks"
                    else ["Invoice", "Amount", "Due Date", "Outstanding Balance", "Receipt State"]
                )
                scope = {"property": "Project Link", "relation": {"contains": project["id"]}}
                if table == "Tasks":
                    scope = {
                        "and": [
                            scope,
                            {
                                "property": "Work Type",
                                "select": {"does_not_equal": "Change request"},
                            },
                        ]
                    }
                spec = view(table, v["name"], columns=fields, filter=scope)
                compiled = compile_view(spec, upgrade.tables["freelancer"][table], "blue")
                patch = {"configuration": compiled["configuration"], "filter": scope}
                upgrade.operation(
                    "studio:polish-existing:" + v["id"],
                    patch,
                    lambda vid=v["id"], p=patch: upgrade.client.mutate("PATCH", "views/" + vid, p),
                )
    foundation = json.loads(Path("state/client-desk-v3.json").read_text(encoding="utf-8"))
    impact = view(
        "Projects",
        "Change impact",
        columns=[
            "Project",
            "Approved Extras",
            "Approved Extra Hours",
            "Pending Change Decisions",
            "Delivery Completion",
        ],
    )
    payload = compile_view(impact, upgrade.tables["freelancer"]["Projects"], "blue")
    payload["database_id"] = foundation["home_modules"]["projects"]["database_id"]
    upgrade.create_view("studio:view:change-impact", payload)
    contexts = [("home", None), ("native-project", native_project)]
    contexts += [(p["id"], p["id"]) for p in upgrade.records["freelancer"]["Projects"]]
    for key, project_id in contexts:
        first = upgrade.state["operations"][f"studio:view:{key}:0"]["result"]
        specs = change_views(project_id)
        compiled = compile_view(specs[0], upgrade.tables["freelancer"]["Tasks"], "blue")
        patch = {"configuration": compiled["configuration"]}
        upgrade.operation(
            "studio:compact-capture:" + key,
            patch,
            lambda vid=first["id"], p=patch: upgrade.client.mutate("PATCH", "views/" + vid, p),
        )
        payload = compile_view(specs[3], upgrade.tables["freelancer"]["Tasks"], "blue")
        payload["database_id"] = first["parent"]["database_id"]
        upgrade.create_view(f"studio:view:{key}:3", payload)
    upgrade.save()


def remove_tracking_links(upgrade):
    """Keep builder ownership in the journal, not clickable buyer-facing text."""
    prefixes = (
        "studio:kit:",
        "studio:changes-label:",
        "studio:home-changes",
        "studio:onboarding",
        "studio:notes-wrapper:",
        "studio:native-kit:",
        "studio:native-changes-label",
        "studio:native-label:",
    )
    for key, op in list(upgrade.state["operations"].items()):
        if not key.startswith(prefixes) or op.get("status") != "done":
            continue
        old = op["result"]["results"][0]
        op_key = "studio:plain-label:" + old["id"]
        if upgrade.state["operations"].get(op_key, {}).get("status") == "done":
            continue
        kind = old["type"]
        parts = []
        changed = False
        for part in old[kind].get("rich_text", []):
            text = part.get("text", {}).get("content", part.get("plain_text", ""))
            url = (part.get("text", {}).get("link") or {}).get("url")
            owned = bool(
                url
                and any(
                    s in url
                    for s in ("#design-web-studio", "#studio-template", "#previous-project-notes")
                )
            )
            changed |= owned
            if owned and text.strip() == "↗":
                continue
            parts.append(rich(text, None if owned else url, **part.get("annotations", {})))
        if not changed:
            continue
        current = upgrade.client.get("blocks/" + old["id"])
        desired = dict(old)
        desired[kind] = dict(old[kind], rich_text=parts)
        if signature(current) not in (signature(old), signature(desired)):
            raise ValueError("Owned label was edited; preserve it for review")
        payload = {kind: {"rich_text": parts}}
        upgrade.operation(
            op_key,
            payload,
            lambda bid=old["id"], p=payload: upgrade.client.mutate("PATCH", "blocks/" + bid, p),
            lambda bid=old["id"], wanted=desired: (
                upgrade.client.get("blocks/" + bid)
                if signature(upgrade.client.get("blocks/" + bid)) == signature(wanted)
                else None
            ),
        )


def main(apply: bool = False, native_only: bool = False, polish_only: bool = False):
    if not apply:
        print(
            "Dry-run: design/web project kit, project intake and estimated/approved change workflow. Existing records and source values retained."
        )
        return
    with upgrade_lock():
        client, upgrade, page_id = load()
        try:
            if native_only and polish_only:
                raise ValueError("Choose one scoped operation")
            if polish_only:
                polish_studio(upgrade, page_id)
                remove_tracking_links(upgrade)
            elif native_only:
                install_native_templates(upgrade)
            else:
                apply_studio(upgrade, page_id)
        finally:
            client.close()


if __name__ == "__main__":
    typer.run(main)

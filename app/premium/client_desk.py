"""Client Desk's plan-compatible home, over the original five data sources.

The reference-library move and full-width preference are performed in Notion UI.
This runner inserts owned blocks/views and missing lifecycle choices. It never
moves or removes user data.
"""

import json
from pathlib import Path

import typer

from app.config import Settings
from app.main import upgrade_lock
from app.premium.client import PremiumClient
from app.premium.upgrade import PremiumUpgrade
from app.premium.views import compile_view, formula_gt, view
from app.services.state import save_json
from app.templates.dashboard import block, rich

REFERENCE = "Reference library · previous setup"
MARKER = "https://www.notion.so/402de7f296f681438078ea81777e9a72#client-desk-home-v3"


def modules():
    open_tasks = {"property": "Remaining Task", "formula": {"number": {"equals": 1}}}
    active = {
        "and": [
            {"property": "Status", "select": {"does_not_equal": label}}
            for label in ("Completed", "Cancelled", "Archived")
        ]
    }
    return [
        (
            "focus",
            "01  /  Focus desk",
            "Finish the next delivery.",
            [
                view(
                    "Tasks",
                    "Next deliveries",
                    "list",
                    ["Project Link", "Due Date", "Priority"],
                    filter=open_tasks,
                    sort="Due Date",
                ),
                view(
                    "Tasks",
                    "All tasks",
                    columns=[
                        "Task",
                        "Project Link",
                        "Due Date",
                        "Priority",
                        "Status",
                        "Hours Logged",
                    ],
                ),
                view(
                    "Tasks",
                    "Delivery calendar",
                    "calendar",
                    ["Project Link", "Status"],
                    date="Due Date",
                ),
            ],
        ),
        (
            "projects",
            "02  /  Delivery studio",
            "A clear next action for every client project.",
            [
                view(
                    "Projects",
                    "Active projects",
                    "gallery",
                    ["Client Link", "Due Date", "Next Action", "Delivery Progress", "Scope Signal"],
                    filter=active,
                    sort="Due Date",
                ),
                view(
                    "Projects",
                    "Scope guard",
                    columns=[
                        "Project",
                        "Included Revisions",
                        "Revisions Used",
                        "Change Request",
                        "Scope Signal",
                    ],
                ),
                view(
                    "Projects",
                    "Project economics",
                    columns=[
                        "Project",
                        "Fee",
                        "Hours Budget",
                        "Logged Hours",
                        "Fee per Logged Hour",
                        "Direct Costs",
                    ],
                ),
            ],
        ),
        (
            "money",
            "03  /  Money desk",
            "Know what is due. Record what has arrived.",
            [
                view(
                    "Invoices",
                    "Unpaid balances",
                    columns=[
                        "Invoice",
                        "Client Link",
                        "Due Date",
                        "Outstanding Balance",
                        "Receipt State",
                    ],
                    filter=formula_gt("Outstanding Balance", 0),
                    sort="Due Date",
                ),
                view(
                    "Invoices",
                    "Overdue",
                    columns=["Invoice", "Client Link", "Due Date", "Overdue Balance"],
                    filter=formula_gt("Overdue Balance", 0),
                    sort="Due Date",
                ),
                view(
                    "Invoices",
                    "Record a payment",
                    columns=[
                        "Invoice",
                        "Amount",
                        "Amount Received",
                        "Payment Status",
                        "Outstanding Balance",
                    ],
                ),
            ],
        ),
        (
            "pipeline",
            "04  /  Next opportunities",
            "Make the next follow-up visible.",
            [
                view(
                    "Leads",
                    "Lead pipeline",
                    "board",
                    ["Service", "Next Follow Up", "Estimated Value"],
                    group="Stage",
                ),
                view(
                    "Leads",
                    "Follow-up list",
                    columns=["Lead", "Stage", "Next Follow Up", "Estimated Value"],
                    sort="Next Follow Up",
                ),
                view(
                    "Clients",
                    "Client rooms",
                    "gallery",
                    ["Company", "Stage", "Outstanding Invoices"],
                ),
            ],
        ),
    ]


def setup():
    pointer = json.loads(Path("state/client-desk-v3-backup.json").read_text(encoding="utf-8"))
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
        raise ValueError("Client Desk parent changed; stop for review.")
    upgrade = PremiumUpgrade(client, snapshot, path, Path("state/client-desk-v3.json"))
    for name in upgrade.tables["freelancer"]:
        upgrade.refresh("freelancer", name)
    return client, upgrade, page_id


def reference(upgrade, page_id):
    toggle = block("toggle", REFERENCE)
    toggle["toggle"]["rich_text"] = [rich(REFERENCE, MARKER)]
    return upgrade.append_owned("home:reference", page_id, [toggle], MARKER, {"type": "start"})[0]


def build_home(upgrade, page_id):
    lifecycle_choices(upgrade)
    schema = upgrade.tables["freelancer"]
    # No dashboard or chart: these views are validated in the signed-in workspace.
    hero = block("paragraph", "A calmer desk. A stronger business.")
    hero["paragraph"]["rich_text"] = [
        rich("A calmer desk. A stronger business.", MARKER, color="gray")
    ]
    roots = upgrade.append_owned("home:hero", page_id, [hero], MARKER, {"type": "start"})
    anchor = roots[-1]["id"]
    created = {}
    for key, heading, subtitle, specs in modules():
        marker = MARKER + "-" + key
        title_block = block("heading_2", heading)
        title_block["heading_2"]["rich_text"] = [rich(heading, marker)]
        group = upgrade.append_owned(
            "home:section:" + key,
            page_id,
            [title_block, block("paragraph", subtitle)],
            marker,
            {"type": "after_block", "after_block": {"id": anchor}},
        )
        anchor = group[-1]["id"]
        first = None
        for index, spec in enumerate(specs):
            payload = compile_view(spec, schema[spec["db"]], "blue")
            if spec["type"] == "gallery":
                payload["configuration"].update(cover_size="medium", card_layout="list")
            if spec["type"] == "board":
                payload["configuration"].pop("cover", None)
                payload["configuration"].update(card_layout="compact")
            if first is None:
                payload["create_database"] = {
                    "parent": {"type": "page_id", "page_id": page_id},
                    "position": {"type": "after_block", "block_id": anchor},
                    "show_data_source_title": False,
                }
            else:
                payload["database_id"] = first["parent"]["database_id"]
            result = upgrade.create_view(f"home:view:{key}:{index}", payload)
            if first is None:
                first = result
                anchor = result["parent"]["database_id"]
                created[key] = {"database_id": anchor, "view_id": result["id"]}
        print("Installed ordinary views:", key, flush=True)
    # Navigation points to the live modules, never fake action buttons.
    cards = []
    for emoji, label, text, key, color in [
        ("↗", "DELIVER", "Tasks, deadlines & project scope", "focus", "blue_background"),
        ("◉", "COLLECT", "Balances, receipts & overdue invoices", "money", "green_background"),
        ("✦", "GROW", "Leads, follow-ups & client rooms", "pipeline", "orange_background"),
    ]:
        url = (
            "https://www.notion.so/"
            + page_id.replace("-", "")
            + "#"
            + created[key]["database_id"].replace("-", "")
        )
        callout = block(
            "callout",
            icon={"type": "emoji", "emoji": {"↗": "📐", "◉": "🧾", "✦": "🤝"}[emoji]},
            color=color,
        )
        callout["callout"]["rich_text"] = [rich(label + "\n", url, bold=True), rich(text)]
        cards.append(
            {
                "object": "block",
                "type": "column",
                "column": {"width_ratio": 1 / 3, "children": [callout]},
            }
        )
    navigation = {"object": "block", "type": "column_list", "column_list": {"children": cards}}
    nav_marker = block("paragraph")
    nav_marker["paragraph"]["rich_text"] = [
        rich("Your studio, at a glance", MARKER + "-nav", color="gray")
    ]
    upgrade.append_owned(
        "home:navigation",
        page_id,
        [nav_marker, navigation],
        MARKER + "-nav",
        {"type": "after_block", "after_block": {"id": roots[-1]["id"]}},
    )
    # Page identity is updated in place, with discovery retaining the original alias.
    payload = {"properties": {"title": {"type": "title", "title": [rich("Client Desk")]}}}
    upgrade.operation(
        "home:page-title",
        payload,
        lambda: upgrade.client.mutate("PATCH", "pages/" + page_id, payload),
        lambda: (
            upgrade.client.get("pages/" + page_id)
            if any(
                p.get("type") == "title"
                and "".join(t.get("plain_text", "") for t in p["title"]) == "Client Desk"
                for p in upgrade.client.get("pages/" + page_id)["properties"].values()
            )
            else None
        ),
    )
    upgrade.state["home_modules"] = created
    upgrade.state["ui_verification_required"] = True
    upgrade.save()
    polish_home(upgrade)
    save_json(
        "reports/client-desk-v3-result.json",
        {
            "page_id": page_id,
            "modules": created,
            "backup": str(upgrade.backup_path),
            "dashboard_views_created": 0,
            "charts_created": 0,
        },
    )


def lifecycle_choices(upgrade):
    """CSV imports only contained used choices; complete the usable workflows."""
    choices = {
        "Tasks": {
            "Status": ["Not started", "In progress", "Waiting", "Done"],
            "Priority": ["High", "Medium", "Low"],
        },
        "Projects": {
            "Status": [
                "Planned",
                "In progress",
                "Client review",
                "On hold",
                "Completed",
                "Cancelled",
                "Archived",
            ]
        },
        "Leads": {"Stage": ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]},
        "Invoices": {"Payment Status": ["Unpaid", "Partial", "Paid", "Cancelled", "Void"]},
        "Clients": {"Stage": ["Prospect", "Active", "Past"]},
    }
    colors = {
        "Done": "green",
        "Completed": "green",
        "Paid": "green",
        "Won": "green",
        "Active": "green",
        "High": "red",
        "Lost": "gray",
        "Cancelled": "gray",
        "Archived": "gray",
        "Partial": "orange",
        "Waiting": "yellow",
        "Client review": "purple",
        "Proposal": "blue",
    }
    for table, fields in choices.items():
        source = upgrade.refresh("freelancer", table)
        updates = {}
        for field, labels in fields.items():
            prop = source["properties"][field]
            if prop["type"] != "select":
                raise ValueError("Lifecycle choice type conflict")
            existing = prop["select"]["options"]
            missing = [name for name in labels if name not in {o["name"] for o in existing}]
            if missing:
                options = [
                    {k: v for k, v in o.items() if k in ("id", "name", "color")} for o in existing
                ]
                options += [
                    {"name": name, "color": colors.get(name, "default")} for name in missing
                ]
                updates[field] = {"select": {"options": options}}
        if updates:
            payload = {"properties": updates}
            upgrade.operation(
                "home:choices:" + table,
                payload,
                lambda sid=source["id"], p=payload: upgrade.client.mutate(
                    "PATCH", "data_sources/" + sid, p
                ),
                lambda table=table, fields=fields: (
                    upgrade.tables["freelancer"][table]
                    if all(
                        set(labels)
                        <= {
                            o["name"]
                            for o in upgrade.refresh("freelancer", table)["properties"][field][
                                "select"
                            ]["options"]
                        }
                        for field, labels in fields.items()
                    )
                    else None
                ),
            )
        upgrade.refresh("freelancer", table)


def polish_home(upgrade):
    """Fix visual ordering and keep ownership markers out of the typography."""
    for key, _, _, specs in modules():
        for index, spec in enumerate(specs):
            view_id = upgrade.state["operations"][f"home:view:{key}:{index}"]["result"]["id"]
            payload = compile_view(spec, upgrade.tables["freelancer"][spec["db"]], "blue")
            configuration = payload["configuration"]
            if spec["type"] == "gallery":
                configuration.update(cover_size="medium", card_layout="list")
            if spec["type"] == "board":
                configuration.pop("cover", None)
                configuration.update(card_layout="compact")
            patch = {"configuration": configuration}
            upgrade.operation(
                f"home:polish-view:{key}:{index}",
                patch,
                lambda vid=view_id, p=patch: upgrade.client.mutate("PATCH", "views/" + vid, p),
                lambda vid=view_id, p=patch: (
                    upgrade.client.get("views/" + vid)
                    if all(
                        upgrade.client.get("views/" + vid).get("configuration", {}).get(k) == v
                        for k, v in p["configuration"].items()
                    )
                    else None
                ),
            )
    operations = ["home:hero", "home:navigation"] + ["home:section:" + key for key, *_ in modules()]
    for operation in operations:
        root = upgrade.state["operations"][operation]["result"]["results"][0]
        kind = root["type"]
        parts = root[kind]["rich_text"]
        text = "".join(p.get("plain_text", p.get("text", {}).get("content", "")) for p in parts)
        marker = next(p["text"]["link"]["url"] for p in parts if p.get("text", {}).get("link"))
        patch = {kind: {"rich_text": [rich(text), rich("\u200b", marker)]}}
        upgrade.operation(
            "home:polish-block:" + root["id"],
            patch,
            lambda bid=root["id"], p=patch: upgrade.client.mutate("PATCH", "blocks/" + bid, p),
            lambda bid=root["id"], p=patch, kind=kind: (
                upgrade.client.get("blocks/" + bid)
                if upgrade.client.get("blocks/" + bid)[kind]["rich_text"] == p[kind]["rich_text"]
                else None
            ),
        )
    board_id = upgrade.state["operations"]["home:view:pipeline:0"]["result"]["id"]
    board_spec = modules()[3][3][0]
    board_config = compile_view(board_spec, upgrade.tables["freelancer"]["Leads"], "blue")[
        "configuration"
    ]
    board_config.pop("cover", None)
    board_config.update(card_layout="compact")
    board_config["group_by"]["hide_empty_groups"] = True
    patch = {"configuration": board_config}
    upgrade.operation(
        "home:hide-empty-lead-groups",
        patch,
        lambda: upgrade.client.mutate("PATCH", "views/" + board_id, patch),
        lambda: (
            upgrade.client.get("views/" + board_id)
            if upgrade.client.get("views/" + board_id)
            .get("configuration", {})
            .get("group_by", {})
            .get("hide_empty_groups")
            else None
        ),
    )


def main(apply: bool = False, reference_only: bool = False, polish_only: bool = False):
    if not apply:
        print(
            "Dry-run: Client Desk home with four ordinary linked modules, 12 views, three navigation cards. No new records or sources."
        )
        return
    with upgrade_lock():
        client, upgrade, page_id = setup()
        try:
            if reference_only and polish_only:
                raise ValueError("Choose one scoped operation.")
            if polish_only:
                polish_home(upgrade)
            elif reference_only:
                root = reference(upgrade, page_id)
                print("Reference toggle:", root["id"])
            else:
                build_home(upgrade, page_id)
        finally:
            client.close()


if __name__ == "__main__":
    typer.run(main)

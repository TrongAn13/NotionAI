"""Isolated client portals and a worked example; never expose master sources."""

import json
from copy import deepcopy
from pathlib import Path

import httpx
import typer

from app.config import Settings
from app.main import upgrade_lock
from app.notion.client import NotionError
from app.notion.discovery import Inventory
from app.premium.client import PremiumClient
from app.premium.studio_content import section, table
from app.premium.upgrade import PremiumUpgrade
from app.premium.views import compile_view, view
from app.services.backup import backup
from app.services.state import read_tree, save_json, signature
from app.templates.dashboard import block, rich

STATE = Path("state/client-experience.json")
POINTER = Path("state/client-experience-backup.json")
HOME = "402de7f2-96f6-8143-8078-ea81777e9a72"


def choice(*names):
    return {"select": {"options": [{"name": n} for n in names]}}


CONTENT = {
    "Content item": {"title": {}},
    "Owner": {"rich_text": {}},
    "Due": {"date": {}},
    "Required": {"checkbox": {}},
    "Asset link": {"url": {}},
    "Received on": {"date": {}},
    "Checked": {"checkbox": {}},
    "Notes": {"rich_text": {}},
    "Readiness": {
        "formula": {
            "expression": 'if(not prop("Required"), "Optional", if(or(empty(prop("Asset link")), empty(prop("Received on"))), "Awaiting content", if(not prop("Checked"), "Needs review", "Ready")))'
        }
    },
}
REVIEWS = {
    "Review": {"title": {}},
    "Version": {"rich_text": {}},
    "Round": {"number": {"format": "number"}},
    "Preview link": {"url": {}},
    "Feedback": {"rich_text": {}},
    "Decision": choice("Awaiting feedback", "Changes requested", "Approved", "Superseded"),
    "Reviewer": {"rich_text": {}},
    "Reviewed on": {"date": {}},
    "Scope check": choice("Within scope", "Estimate needed", "Extra agreed"),
    "Review gate": {
        "formula": {
            "expression": 'if(prop("Decision") == "Superseded", "Superseded", if(prop("Decision") != "Approved", "Open", if(or(empty(prop("Version")), or(empty(prop("Preview link")), or(empty(prop("Reviewer")), empty(prop("Reviewed on"))))), "Complete approval record", "Recorded approval")))'
        }
    },
}
ACTIVITY = {
    "Update": {"title": {}},
    "Date": {"date": {}},
    "Type": choice("Kickoff", "Decision", "Progress", "Handoff"),
    "Summary": {"rich_text": {}},
    "Next action": {"rich_text": {}},
    "Owner": {"rich_text": {}},
    "Due": {"date": {}},
}


def notice(text, emoji="✨", color="blue_background"):
    return block("callout", text, icon={"type": "emoji", "emoji": emoji}, color=color)


def link(label, pid):
    b = block("paragraph")
    b["paragraph"]["rich_text"] = [rich(label, "https://www.notion.so/" + pid.replace("-", ""))]
    return b


def portal_blocks(demo=False):
    name = "NORTHSTAR COFFEE / WEBSITE" if demo else "[CLIENT] / [PROJECT]"
    return [
        notice(name + "\nYour project, decisions and next steps — in one place.", "🎨"),
        notice(
            "FICTIONAL WALKTHROUGH · Dates, approvals, assets and amounts below are examples, not live client records."
            if demo
            else "START HERE · Replace bracketed prompts. Add project-specific content and review the portal before inviting your client.",
            "🧭",
            "gray_background",
        ),
        table(
            ["Project snapshot", "What we agreed"],
            [
                [
                    "Outcome",
                    "Turn local visitors into coffee subscription enquiries."
                    if demo
                    else "[Business outcome and success measure]",
                ],
                [
                    "Deliverables",
                    "5-page website; responsive layouts; CMS handoff."
                    if demo
                    else "[Exact pages/assets, formats and acceptance checks]",
                ],
                [
                    "Current stage",
                    "Review round 2 complete; extra landing page awaiting estimate."
                    if demo
                    else "[Current milestone and next date]",
                ],
                [
                    "Approver",
                    "Mia · fictional founder" if demo else "[One person consolidating feedback]",
                ],
                [
                    "Next action",
                    "Designer estimates the subscription landing page before starting it."
                    if demo
                    else "[Who does what, by when]",
                ],
            ],
        ),
        block("heading_2", "01 / Project route"),
        table(
            ["Milestone", "Completion condition", "Example status" if demo else "Status / date"],
            [
                [
                    "Discover",
                    "Outcome, scope and approver confirmed",
                    "Complete · 5 Oct" if demo else "[Status / date]",
                ],
                [
                    "Prepare",
                    "Required content checked",
                    "Complete · 8 Oct" if demo else "[Status / date]",
                ],
                [
                    "Design",
                    "Named version reviewed by approver",
                    "Approved · v2 · 16 Oct" if demo else "[Status / date]",
                ],
                [
                    "Build & launch",
                    "Device, content and functional checks completed",
                    "Planned · 26 Oct" if demo else "[Status / date]",
                ],
                [
                    "Handoff",
                    "Assets, access and training received",
                    "Planned · 28 Oct" if demo else "[Status / date]",
                ],
            ],
        ),
        block("heading_2", "02 / Content we need from you"),
        block(
            "paragraph",
            "Open an item to add the asset link and received date. The designer checks suitability before marking Checked. Use your approved file storage for files; keep passwords in a password manager.",
        ),
        block("heading_2", "03 / Review room"),
        block(
            "paragraph",
            "One row = one version and review round. Open the row, inspect its preview, consolidate feedback and record the decision, reviewer and date. A recorded approval is a manual record, not a verified signature.",
        ),
        section(
            "How to give useful feedback",
            [
                block(
                    "numbered_list_item",
                    "Identify the page/screen and version, then explain the issue and desired result.",
                ),
                block(
                    "numbered_list_item",
                    "Combine stakeholder feedback into one response from the approver.",
                ),
                block(
                    "numbered_list_item",
                    "Keep older rounds. Mark replaced versions Superseded; create a new row for the next round.",
                ),
                block(
                    "numbered_list_item",
                    "New pages or deliverables need a scope estimate before work begins. Scope check does not authorize extra fees.",
                ),
            ],
        ),
        block("heading_2", "04 / Decisions & next steps"),
        block(
            "paragraph",
            "Meeting notes should end with a decision, an owner and the next date. Update this log after each client conversation.",
        ),
        block("heading_2", "05 / Handoff & support"),
        table(
            ["Handoff item", "Location / confirmation"],
            [
                ["Final files", "[Reviewed export or source-file link]"],
                ["Training", "[Recording or handoff guide]"],
                ["Access transfer", "[Confirm ownership through the service; no passwords here]"],
                ["Acceptance", "[Named approver, date and remaining exceptions]"],
                ["Support window", "[Agreed dates and contact method]"],
            ],
        ),
    ]


def guide_blocks():
    return [
        notice(
            "CLIENT EXPERIENCE STUDIO\nPrepare → collect → review → agree changes → hand off.", "🧩"
        ),
        block(
            "paragraph",
            "Use the blank portal for each client. Explore the fictional example first; it uses separate sources so sample approvals and amounts never enter your live business totals.",
        ),
        block("heading_2", "Your first portal in 10 minutes"),
        block(
            "numbered_list_item",
            "Open Client portal · blank master. Duplicate the entire page in Notion, including its inline databases. Rename the copy for one client.",
        ),
        block(
            "numbered_list_item",
            "Fill the project snapshot and milestone dates. Add only the content requests and preview links intended for that client.",
        ),
        block(
            "numbered_list_item",
            "Create one review row per version. Open the row to add consolidated feedback, reviewer and date. Required fields drive the review gate.",
        ),
        block(
            "numbered_list_item",
            "Keep business fees, cost estimates and other clients in Client Desk. The portal databases have no relations or linked views into your internal sources.",
        ),
        block(
            "numbered_list_item",
            "Review every page, attachment and link in the copy, then choose the appropriate guest permissions. The builder has not published or shared any page.",
        ),
        section(
            "Connect client feedback to Scope Guard",
            [
                block(
                    "numbered_list_item",
                    "If feedback adds a deliverable, set Scope check = Estimate needed in the portal review row.",
                ),
                block(
                    "numbered_list_item",
                    "In the internal project's Change desk, create a Change request. Copy the exact request and reference the portal review row in its notes.",
                ),
                block(
                    "numbered_list_item",
                    "Estimate fee, hours and date impact; ask the client to confirm. Record approval evidence and decision date in the internal Change request.",
                ),
                block(
                    "numbered_list_item",
                    "When Change Gate = Approved, create a separate Delivery task linked to that project. Adjust the invoice and dates deliberately, then update the client-visible milestone.",
                ),
                block(
                    "paragraph",
                    "Portal approval and internal Scope Guard are intentionally separate manual records. Editing Scope check does not change invoices or start work automatically.",
                ),
            ],
        ),
        section(
            "Portal sharing check",
            [
                block("to_do", "The copy contains only one client's material.", checked=False),
                block(
                    "to_do",
                    "Each inline database belongs to this copy, not to the blank master or another portal.",
                    checked=False,
                ),
                block(
                    "to_do",
                    "Preview and file links have the intended access; no credentials, internal costs or unrelated client links.",
                    checked=False,
                ),
                block(
                    "to_do",
                    "Guest role and access are verified using a separate account before real client use.",
                    checked=False,
                ),
            ],
        ),
        block("heading_2", "What this release does"),
        block(
            "paragraph",
            "Content readiness, versioned reviews and decision logs work inside each portal. Payment sending, verified signatures, email delivery and cross-workspace synchronization are not configured. The live workspace stays private until you choose to share.",
        ),
    ]


def example_blocks():
    return [
        notice(
            "NORTHSTAR / FROM BRIEF TO HANDOFF\nA fictional five-page website, one extra request and a clear decision trail.",
            "☕",
        ),
        block(
            "paragraph",
            "Training example only. All names, dates, approvals and amounts are fictional. No example values are added to the internal Clients, Projects, Tasks, Leads or Invoices sources.",
        ),
        table(
            ["Step", "What happens", "Where to act"],
            [
                [
                    "1 · Brief",
                    "Mia wants more subscription enquiries. Agree five pages, two design rounds and a 28 October handoff.",
                    "Project Discovery brief + scope",
                ],
                [
                    "2 · Content",
                    "Logo and approved copy arrive. A low-resolution photo stays Needs review until replaced.",
                    "Portal → Content inbox",
                ],
                [
                    "3 · Review",
                    "v1 requests a clearer mobile CTA. v2 records Mia's approval on 16 October; v1 stays in history.",
                    "Portal → Review room",
                ],
                [
                    "4 · Scope change",
                    "A separate subscription landing page was not in the five-page scope. Stop and estimate it.",
                    "Portal Scope check → internal Change request",
                ],
                [
                    "5 · Estimate",
                    "Illustrative: +200 USD, +3 hours, +2 days. These totals remain zero until internal approval conditions are met.",
                    "Change desk → Estimate & approval",
                ],
                [
                    "6 · Execute",
                    "After confirmation: record evidence/date, create the delivery task, update the invoice and agree the revised milestone.",
                    "Internal Delivery + Money desk; then portal milestone",
                ],
                [
                    "7 · Handoff",
                    "Check devices and forms, deliver source files and training, record exceptions and acceptance.",
                    "Project launch checklist + portal Handoff",
                ],
                [
                    "8 · Close",
                    "Reconcile actual receipts separately; collect feedback and record what to improve next time.",
                    "Money desk + project debrief",
                ],
            ],
        ),
        section(
            "Example change summary — copy and adapt",
            [
                block(
                    "quote",
                    "The subscription landing page is outside the agreed five-page scope. I estimate an additional 200 USD and three hours, moving the target by two days. Please confirm the deliverable, fee and revised date before I begin. This is a fictional example, not an offer or approval.",
                ),
            ],
        ),
        section(
            "Example handoff message — copy and adapt",
            [
                block(
                    "quote",
                    "Your agreed website deliverables are ready for review. Please check the final files, training guide and access-transfer checklist in your portal. Reply with acceptance or list any exceptions against the agreed scope. The separate payment record shows what remains due.",
                ),
            ],
        ),
    ]


class ExperienceClient(PremiumClient):
    """Creation restricted to explicitly registered project-owned containers."""

    def __init__(self, settings):
        super().__init__(settings)
        self.creation_parents = {HOME}
        self.owned_rows = set()

    def patch_owned_row(self, bid, cells):
        if bid not in self.owned_rows:
            raise ValueError("Table row is outside the owned portal scope")
        self.sleep(self.interval)
        try:
            response = self.http.patch("blocks/" + bid, json={"table_row": {"cells": cells}})
        except httpx.TransportError:
            raise NotionError("Row outcome unknown; reconcile before retrying.") from None
        return self._result(response)

    def create(self, endpoint, payload):
        parent = payload.get("parent", {})
        pid = parent.get("page_id") or parent.get("data_source_id")
        if endpoint not in ("pages", "databases") or pid not in self.creation_parents:
            raise ValueError("Creation parent is outside the owned client-experience scope")
        self.sleep(self.interval)
        try:
            response = self.http.post(endpoint, json=payload)
        except httpx.TransportError:
            raise NotionError(
                "Creation outcome unknown; reconcile journal before retrying."
            ) from None
        return self._result(response)


def prepare(client):
    if POINTER.exists():
        path = Path(json.loads(POINTER.read_text(encoding="utf-8"))["path"])
        return path, json.loads(path.read_text(encoding="utf-8"))
    inventory = Inventory.model_validate_json(
        Path("reports/inventory.json").read_text(encoding="utf-8")
    )
    inventory.templates["freelancer"]["page"] = client.get("pages/" + HOME)
    path, snapshot = backup(client, inventory, ["freelancer"])
    native = json.loads(Path("state/client-desk-studio.json").read_text(encoding="utf-8"))[
        "native_templates"
    ]
    snapshot["native_templates"] = {}
    for label, info in native.items():
        snapshot["native_templates"][label] = {
            "page": client.get("pages/" + info["id"]),
            "blocks": [read_tree(client, b) for b in client.children(info["id"])],
        }
    save_json(path, snapshot)
    save_json(POINTER, {"path": str(path)})
    return path, snapshot


def create_page(upgrade, key, parent, name, children, cover):
    client = upgrade.client
    client.creation_parents.add(parent)
    payload = {
        "parent": {"type": "page_id", "page_id": parent},
        "properties": {"title": {"type": "title", "title": [rich(name)]}},
        "icon": {"type": "emoji", "emoji": "☕" if "Northstar" in name else "🎨"},
        "cover": {"type": "file_upload", "file_upload": {"id": cover}},
        "children": children,
    }

    def recover():
        matches = [
            b
            for b in client.children(parent)
            if b["type"] == "child_page" and b["child_page"]["title"] == name
        ]
        if len(matches) == 1:
            candidate = client.get("pages/" + matches[0]["id"])
            roots = list(client.children(candidate["id"]))
            if [signature(read_tree(client, b)) for b in roots] == [signature(b) for b in children]:
                return candidate
        return None

    page = upgrade.operation(
        "experience:page:" + key, payload, lambda: client.create("pages", payload), recover
    )
    client.creation_parents.add(page["id"])
    return page


def append(upgrade, key, pid, children, position=None):
    payload = {"children": children}
    if position:
        payload["position"] = position
    return upgrade.operation(
        "experience:append:" + key,
        payload,
        lambda: upgrade.client.mutate("PATCH", "blocks/" + pid + "/children", payload),
    )


def create_db(upgrade, key, pid, name, fields):
    client = upgrade.client
    payload = {
        "parent": {"type": "page_id", "page_id": pid},
        "title": [rich(name)],
        "is_inline": True,
        "initial_data_source": {"properties": fields},
    }

    def recover():
        matches = [
            b
            for b in client.children(pid)
            if b["type"] == "child_database" and b["child_database"]["title"] == name
        ]
        return client.get("databases/" + matches[0]["id"]) if len(matches) == 1 else None

    result = upgrade.operation(
        "experience:db:" + key, payload, lambda: client.create("databases", payload), recover
    )
    sid = result["data_sources"][0]["id"]
    client.creation_parents.add(sid)
    return result, client.get("data_sources/" + sid)


def record(upgrade, key, sid, props, children=()):
    payload = {
        "parent": {"type": "data_source_id", "data_source_id": sid},
        "properties": props,
        "children": list(children),
    }

    def recover():
        title_key = next(n for n, p in props.items() if "title" in p)
        wanted = signature(block("paragraph", ""))
        wanted["rich_text"] = signature(
            {"type": "paragraph", "paragraph": {"rich_text": props[title_key]["title"]}}
        )["rich_text"]
        matches = []
        for row in upgrade.client.query(sid):
            title = row["properties"][title_key]["title"]
            if signature({"type": "paragraph", "paragraph": {"rich_text": title}}) == wanted:
                actual = [
                    signature(read_tree(upgrade.client, b))
                    for b in upgrade.client.children(row["id"])
                ]
                if actual == [signature(b) for b in children]:
                    matches.append(row)
        return matches[0] if len(matches) == 1 else None

    return upgrade.operation(
        "experience:record:" + key,
        payload,
        lambda: upgrade.client.create("pages", payload),
        recover,
    )


def text(value):
    return {"rich_text": [rich(value)]}


def seed_demo(upgrade, sources):
    for i, (name, asset, received, checked, note) in enumerate(
        [
            (
                "Brand logo / SVG",
                "https://example.com/northstar/logo",
                "2026-10-06",
                True,
                "Example asset URL; replace with a real reviewed file.",
            ),
            (
                "Approved website copy",
                "https://example.com/northstar/copy",
                "2026-10-07",
                True,
                "Five pages of copy approved in this fictional example.",
            ),
            (
                "Product photography",
                "https://example.com/northstar/photos",
                "2026-10-08",
                False,
                "Low-resolution images; request originals before launch.",
            ),
            (
                "Subscription offer details",
                None,
                None,
                False,
                "New landing-page input; confirm scope before commissioning.",
            ),
        ]
    ):
        record(
            upgrade,
            f"demo-content-{i}",
            sources["content"]["id"],
            {
                "Content item": {"title": [rich(name)]},
                "Owner": text("Mia · fictional client"),
                "Due": {"date": {"start": "2026-10-09"}},
                "Required": {"checkbox": True},
                "Asset link": {"url": asset},
                "Received on": {"date": {"start": received} if received else None},
                "Checked": {"checkbox": checked},
                "Notes": text(note),
            },
        )
    for i, (version, decision, feedback, scope, reviewer, day) in enumerate(
        [
            (
                "v1",
                "Superseded",
                "Make the mobile subscription CTA easier to find.",
                "Within scope",
                "Mia · fictional approver",
                "2026-10-13",
            ),
            (
                "v2",
                "Approved",
                "Mobile CTA now meets the agreed acceptance check.",
                "Within scope",
                "Mia · fictional approver",
                "2026-10-16",
            ),
            (
                "extra-page-v1",
                "Changes requested",
                "Add a standalone subscription landing page beyond the five-page scope.",
                "Estimate needed",
                "Mia · fictional approver",
                "2026-10-17",
            ),
        ]
    ):
        record(
            upgrade,
            f"demo-review-{i}",
            sources["reviews"]["id"],
            {
                "Review": {
                    "title": [
                        rich("Homepage / " + version if i < 2 else "New subscription landing page")
                    ]
                },
                "Version": text(version),
                "Round": {"number": min(i + 1, 2)},
                "Preview link": {"url": "https://example.com/northstar/" + version},
                "Feedback": text(feedback),
                "Decision": {"select": {"name": decision}},
                "Reviewer": text(reviewer),
                "Reviewed on": {"date": {"start": day}},
                "Scope check": {"select": {"name": scope}},
            },
            [
                block(
                    "paragraph",
                    "Fictional example. Preview URL is a placeholder, not a delivered design.",
                ),
                block("heading_3", "Consolidated feedback"),
                block("paragraph", feedback),
            ],
        )
    for i, (name, day, kind, summary, action, owner) in enumerate(
        [
            (
                "Kickoff / five pages agreed",
                "2026-10-05",
                "Kickoff",
                "Five pages, two design rounds and one named approver.",
                "Provide approved copy and logo",
                "Mia",
            ),
            (
                "Homepage / v2 approved",
                "2026-10-16",
                "Decision",
                "The second version resolves the mobile CTA feedback.",
                "Continue the agreed build checks",
                "Designer",
            ),
            (
                "Extra page / estimate first",
                "2026-10-17",
                "Decision",
                "The subscription landing page is outside the baseline scope.",
                "Estimate fee and revised date; request confirmation",
                "Designer",
            ),
        ]
    ):
        record(
            upgrade,
            f"demo-activity-{i}",
            sources["activity"]["id"],
            {
                "Update": {"title": [rich(name)]},
                "Date": {"date": {"start": day}},
                "Type": {"select": {"name": kind}},
                "Summary": text(summary),
                "Next action": text(action),
                "Owner": text(owner + " · fictional"),
            },
        )


def install_portal(upgrade, page, demo):
    client = upgrade.client
    roots = list(client.children(page["id"]))
    headings = {
        "".join(t.get("plain_text", "") for t in b[b["type"]].get("rich_text", [])): b["id"]
        for b in roots
        if b["type"] == "heading_2"
    }
    sources = {}
    for label, name, fields, columns, heading in [
        (
            "content",
            "Content inbox",
            CONTENT,
            ["Content item", "Owner", "Due", "Readiness"],
            "02 / Content we need from you",
        ),
        (
            "reviews",
            "Review room",
            REVIEWS,
            ["Review", "Version", "Decision", "Scope check", "Review gate"],
            "03 / Review room",
        ),
        (
            "activity",
            "Decision log",
            ACTIVITY,
            ["Update", "Date", "Next action", "Owner"],
            "04 / Decisions & next steps",
        ),
    ]:
        key = ("example" if demo else "master") + ":" + label
        database, source = create_db(upgrade, key, page["id"], name, fields)
        sources[label] = source
        # Move only our newly created database block immediately after its explanatory paragraph.
        anchor = headings[heading]
        index = next(i for i, b in enumerate(roots) if b["id"] == anchor)
        if index + 1 < len(roots) and roots[index + 1]["type"] == "paragraph":
            anchor = roots[index + 1]["id"]
        payload = compile_view(view(label, name, columns=columns), source, "blue")
        payload["database_id"] = database["id"]
        existing_views = list(client.list_views(database["id"]))
        if existing_views:
            vid = existing_views[0]["id"]
            patch = {k: v for k, v in payload.items() if k not in ("database_id", "data_source_id")}
            upgrade.operation(
                "experience:view:" + key,
                patch,
                lambda v=vid, p=patch: client.mutate("PATCH", "views/" + v, p),
            )
        else:
            upgrade.create_view("experience:view:" + key, payload)
        # Block move is unavailable in the transport; retain the source at the bottom,
        # and put an ordinary linked view in the reader's workflow position.
        linked = compile_view(view(label, name, columns=columns), source, "blue")
        linked["create_database"] = {
            "parent": {"type": "page_id", "page_id": page["id"]},
            "position": {"type": "after_block", "block_id": anchor},
            "show_data_source_title": False,
        }
        upgrade.create_view("experience:positioned-view:" + key, linked)
    if demo:
        seed_demo(upgrade, sources)
    upgrade.state.setdefault("portals", {})["example" if demo else "master"] = {
        "page_id": page["id"],
        "sources": {k: s["id"] for k, s in sources.items()},
    }
    upgrade.save()


def apply():
    with upgrade_lock():
        client = ExperienceClient(Settings.load())
        try:
            path, snapshot = prepare(client)
            snapshot = deepcopy(snapshot)
            snapshot["inventory"]["templates"] = {
                "freelancer": snapshot["inventory"]["templates"]["freelancer"]
            }
            upgrade = PremiumUpgrade(client, snapshot, path, STATE)
            cover = upgrade.operation(
                "experience:cover",
                {"file": "assets/banners/freelancer-v2.png"},
                lambda: {"id": client.upload("assets/banners/freelancer-v2.png")},
            )["id"]
            hub = create_page(
                upgrade, "hub", HOME, "Client Experience Studio", guide_blocks(), cover
            )
            master = create_page(
                upgrade, "master", hub["id"], "Client portal · blank master", portal_blocks(), cover
            )
            example = create_page(
                upgrade,
                "example",
                hub["id"],
                "Northstar · example client portal",
                portal_blocks(True),
                cover,
            )
            story = create_page(
                upgrade, "story", hub["id"], "Northstar · worked project", example_blocks(), cover
            )
            for page, demo in [(master, False), (example, True)]:
                install_portal(upgrade, page, demo)
            append(
                upgrade,
                "hub-navigation",
                hub["id"],
                [
                    link("01 → Duplicate the blank client portal", master["id"]),
                    link("02 → Explore the example client portal", example["id"]),
                    link("03 → Follow the worked project", story["id"]),
                ],
                {"type": "start"},
            )
            append(
                upgrade,
                "story-portal",
                story["id"],
                [link("Open Northstar's example portal", example["id"])],
                {"type": "start"},
            )
            append(
                upgrade,
                "home-entry",
                HOME,
                [
                    notice(
                        "CLIENT EXPERIENCE\nCollect content. Review versions. Keep decisions clear.",
                        "🎨",
                    ),
                    link("Open Client Experience Studio →", hub["id"]),
                ],
                {"type": "start"},
            )
            native = json.loads(Path("state/client-desk-studio.json").read_text(encoding="utf-8"))[
                "native_templates"
            ]["Projects"]["id"]
            append(
                upgrade,
                "project-template-entry",
                native,
                [
                    section(
                        "Client portal / content & reviews",
                        [
                            link("Open Client Experience Studio", hub["id"]),
                            block(
                                "paragraph",
                                "Duplicate the blank portal for this client. Keep this project's internal costs and invoices here; put client-safe content, review versions and decisions in the portal copy. Record its link below.",
                            ),
                            block("paragraph", "Portal link: [paste this client's portal URL]"),
                        ],
                    )
                ],
            )
            upgrade.state.setdefault("pages", {}).update(
                {
                    "hub": hub["id"],
                    "master": master["id"],
                    "example": example["id"],
                    "story": story["id"],
                }
            )
            upgrade.save()
            print(
                json.dumps(
                    {"pages": upgrade.state["pages"], "portals": upgrade.state["portals"]}, indent=2
                )
            )
        finally:
            client.close()


if __name__ == "__main__":
    typer.run(apply)

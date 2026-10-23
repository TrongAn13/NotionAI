"""Editable client-work documents for a solo web/design studio."""

from html import escape

from app.templates.dashboard import block, rich


def table(headers, rows):
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {"cells": [[rich(str(cell))] for cell in row]},
                }
                for row in [headers, *rows]
            ],
        },
    }


def section(name, children):
    return block("toggle", name, children=children)


def project_kit(marker):
    introduction = block("callout", icon={"type": "emoji", "emoji": "📐"}, color="blue_background")
    introduction["callout"]["rich_text"] = [
        rich("DESIGN / WEB PROJECT STUDIO", marker, bold=True),
        rich("\nOne brief. One agreed scope. A clear handoff."),
    ]
    return [
        introduction,
        section(
            "01  /  Discovery brief",
            [
                block(
                    "paragraph",
                    "Complete this with the client before proposing a solution. Replace bracketed prompts; no sample commitments are agreed by default.",
                ),
                table(
                    ["Decision", "Your project"],
                    [
                        ["Business outcome", "[What must improve, and why now?]"],
                        [
                            "Primary audience",
                            "[Who is using this, and what action should they take?]",
                        ],
                        ["Success measure", "[A measurable outcome and review date]"],
                        ["Approver", "[One person who consolidates feedback and signs off]"],
                        [
                            "Deliverables",
                            "[Pages, screens, identity assets, formats and quantities]",
                        ],
                        [
                            "Content & assets",
                            "[Who provides copy, photography, logos and access; due dates]",
                        ],
                        [
                            "Platform & constraints",
                            "[CMS, hosting, integrations, devices and accessibility needs]",
                        ],
                        [
                            "Dependencies",
                            "[Third-party availability, client feedback and launch constraints]",
                        ],
                    ],
                ),
                block(
                    "to_do",
                    "Record Target Outcome, Success Measure and Approval Contact in the project properties.",
                    checked=False,
                ),
                block(
                    "to_do",
                    "Confirm the content deadline and Client Assets Ready before scheduling production.",
                    checked=False,
                ),
            ],
        ),
        section(
            "02  /  Proposal & scope builder",
            [
                block("paragraph", "Proposal for [client] · [project] · prepared [date]"),
                block(
                    "quote",
                    "We will create [deliverables] for [audience] to support [business outcome]. We will assess success using [measure].",
                ),
                table(
                    ["Deliverable", "Quantity / format", "Acceptance check"],
                    [
                        [
                            "[Website / identity / landing page]",
                            "[Exact pages, screens or assets]",
                            "[Observable completion condition]",
                        ],
                        [
                            "[Responsive variations]",
                            "[Agreed devices / breakpoints]",
                            "[Reviewed and approved by named approver]",
                        ],
                        [
                            "[Handoff / training]",
                            "[File formats, documentation and session]",
                            "[Client can access and use the delivered assets]",
                        ],
                    ],
                ),
                table(
                    ["Boundary", "Agreement to complete"],
                    [
                        ["Included", "[List what the fee covers; specify revision rounds]"],
                        [
                            "Excluded",
                            "[Copywriting, photography, extra pages, hosting, integrations or other exclusions]",
                        ],
                        [
                            "Milestones",
                            "[Discovery → first direction → review → handoff, with dates and owners]",
                        ],
                        [
                            "Fee & payment schedule",
                            "[Fee, currency and milestone payments; enter invoices separately]",
                        ],
                        [
                            "Feedback",
                            "[One consolidated response from the approver within an agreed window]",
                        ],
                        [
                            "Changes",
                            "[Estimate extra work and record approval before changing fee or delivery dates]",
                        ],
                    ],
                ),
                block(
                    "to_do",
                    "Confirm the proposal with the client; then check Scope Agreed and set Included Revisions.",
                    checked=False,
                ),
            ],
        ),
        section(
            "03  /  Scope Guard — request to decision",
            [
                block(
                    "numbered_list_item",
                    "Open Change desk → Capture request. Set Work Type = Change request and link this project.",
                ),
                block(
                    "numbered_list_item",
                    "Describe the requested outcome, what differs from scope, and the deliverable affected. Estimate Extra Fee, Extra Hours and Deadline Impact Days; check Estimate Reviewed, including when the estimate is zero.",
                ),
                block(
                    "numbered_list_item",
                    "Send the change summary manually. Record Decision and an Approval Evidence URL to the client's written confirmation. Decision On records when it was agreed.",
                ),
                block(
                    "numbered_list_item",
                    "Approved Extra Fee/Hours count only when Decision = Approved, Estimate Reviewed is checked and evidence is recorded. Approval records your decision trail; it is not a signature workflow.",
                ),
                block(
                    "numbered_list_item",
                    "For approved work, create a separate Delivery task and adjust the actual deadline/invoice yourself. The request row stays as the decision history.",
                ),
                block(
                    "quote",
                    "Thanks for the request to [change]. It adds [deliverable] beyond [agreed scope]. The additional fee is [amount and currency], estimated effort [hours], and proposed schedule impact [days / revised date]. Please confirm the revised scope, fee and date in writing before we schedule it.",
                ),
            ],
        ),
        section(
            "04  /  Design & launch quality gate",
            [
                *[
                    block("to_do", text, checked=False)
                    for text in [
                        "Confirm all agreed pages/assets are present and the final copy is approved.",
                        "Review desktop, tablet and phone layouts on real devices.",
                        "Test links, navigation, forms and the destination of submitted messages.",
                        "Check keyboard navigation, visible focus, labels, contrast and image descriptions.",
                        "Check image sizes, page loading, favicon and sharing previews.",
                        "Confirm the agreed domains, redirects, integrations and tracking choices.",
                        "Resolve review comments or record the agreed exceptions.",
                        "Capture the approver's acceptance before marking Handoff Accepted.",
                    ]
                ],
            ],
        ),
        section(
            "05  /  Handoff pack & client email",
            [
                table(
                    ["Asset", "Location / owner"],
                    [
                        ["Final deliverables", "[Final file / site links and version]"],
                        ["Editable source files", "[Design/source links and ownership handoff]"],
                        ["Usage guide & training", "[Documentation and recording links]"],
                        [
                            "Access transfer",
                            "[Use a secure password manager; do not store passwords here]",
                        ],
                        [
                            "Post-launch support",
                            "[Included support window, contact method and exclusions]",
                        ],
                        ["Remaining work", "[Known limitations, owner and due date]"],
                    ],
                ),
                block(
                    "quote",
                    "Hi [name], your [project] is ready for handoff. Final deliverables: [link]. Editable sources: [link]. Getting-started guide: [link]. Please review against our agreed acceptance checks and send one consolidated response by [date]. Included support: [scope/window]. Remaining invoice: [reference, amount/currency, due date]. Thank you for collaborating on this project.",
                ),
                block(
                    "to_do",
                    "Check the Money desk for actual remaining invoice balances; do not assume handoff means payment is received.",
                    checked=False,
                ),
            ],
        ),
        section(
            "06  /  Project debrief",
            [
                block(
                    "paragraph",
                    "What helped the client reach the intended outcome? [Evidence / result]",
                ),
                block(
                    "paragraph",
                    "Where did scope, time or feedback differ from the plan? [One cause]",
                ),
                block("paragraph", "What will change in the next proposal? [One specific action]"),
                block(
                    "quote",
                    "Hi [name], now that [project] is in use, what has improved for you? If you are happy to share a short testimonial, which result and part of the collaboration would you mention? Please confirm how you would like your name/company attributed.",
                ),
            ],
        ),
    ]


def to_html(blocks):
    """Clipboard HTML for the native Notion database-template editor."""
    output = []
    for b in blocks:
        kind = b["type"]
        body = b[kind]
        text = "".join(p.get("text", {}).get("content", "") for p in body.get("rich_text", []))
        text = text.replace("\u200b", "")
        if kind == "table":
            rows = []
            for row in body["children"]:
                rows.append(
                    "<tr>"
                    + "".join(
                        "<td>" + escape("".join(p["text"]["content"] for p in cell)) + "</td>"
                        for cell in row["table_row"]["cells"]
                    )
                    + "</tr>"
                )
            output.append("<table>" + "".join(rows) + "</table>")
        elif kind == "toggle":
            output.append("<h2>" + escape(text) + "</h2>" + to_html(body.get("children", [])))
        else:
            tag = "blockquote" if kind in ("quote", "callout") else "p"
            if kind == "to_do":
                text = "☐ " + text
            output.append(f"<{tag}>" + escape(text).replace("\n", "<br>") + f"</{tag}>")
    return "".join(output)

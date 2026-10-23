"""Customer-facing dashboard content; database links use discovered resource IDs."""

from app.services.state import digest, signature
from app.templates.catalog import VERSION


def rich(text, url=None, **annotations):
    item = {"type": "text", "text": {"content": text}}
    if url:
        item["text"]["link"] = {"url": url}
    if annotations:
        item["annotations"] = annotations
    return item


def block(kind, text="", **settings):
    body = {} if kind == "divider" else {"rich_text": [rich(text)]}
    body.update(settings)
    return {"object": "block", "type": kind, kind: body}


def title(database):
    return "".join(
        t.get("plain_text", t.get("text", {}).get("content", "")) for t in database.get("title", [])
    )


def dashboard(spec, entry, marker):
    blocks = [
        block(
            "callout",
            spec.tagline,
            icon={"type": "emoji", "emoji": spec.icon},
            color="blue_background",
        ),
        block("heading_2", "Welcome"),
        block(
            "paragraph",
            f"Welcome to {spec.title}. Start with one real workflow, then tailor the workspace to your needs.",
        ),
        block("heading_2", "Quick start"),
        block(
            "numbered_list_item",
            "Explore the existing databases below. Keep useful records and review any fictional starter examples.",
        ),
        block(
            "numbered_list_item",
            "Follow the sample workflow and enter your own real information. New number fields start empty; fill them before interpreting calculated results.",
        ),
        block(
            "numbered_list_item",
            "Complete the recommended views and formatting in the setup checklist. Review your dashboard weekly.",
        ),
        block("divider"),
        block("heading_2", "What you can do"),
    ]
    blocks += [block("bulleted_list_item", text) for text in spec.features]
    blocks += [block("heading_2", "Database navigation")]
    for database in entry["databases"]:
        meta = database["metadata"]
        url = meta.get("url") or f"https://www.notion.so/{meta['id'].replace('-', '')}"
        item = block("paragraph")
        item["paragraph"]["rich_text"] = [rich(title(meta) or "Open database", url)]
        blocks.append(item)
    blocks += [block("heading_2", "Sample workflow")]
    blocks += [block("numbered_list_item", text) for text in spec.workflow]
    if spec.prompts:
        blocks += [
            block("heading_2", "AI prompt library"),
            block(
                "paragraph",
                "Replace bracketed placeholders. Review generated content for accuracy, originality and tone before use.",
            ),
        ]
        blocks += [block("bulleted_list_item", prompt) for prompt in spec.prompts]
    blocks += [
        block("heading_2", "Make it yours"),
        block(
            "paragraph",
            "Choose your labels, colors and preferred views. Existing columns and records remain yours. Avoid renaming formula inputs until you have checked the calculation. Application-added calculations use the NTB prefix.",
        ),
        block("heading_2", "Setup checklist"),
    ]
    blocks += [block("to_do", text, checked=False) for text in spec.manual]
    blocks += [
        block("heading_2", "Help & FAQ"),
        block(
            "paragraph",
            "Where do I begin? Follow Quick start, then open one database. Start small and expand once the workflow is comfortable.",
        ),
        block(
            "paragraph",
            "Why is a calculation empty or zero? Check its source fields, dates and exact status labels. Ratios with an empty or zero target return zero; an empty deadline stays blank.",
        ),
        block(
            "paragraph",
            "Will this connect my other apps? This workspace organizes information entered here. External imports, notifications and publishing are not configured.",
        ),
        block(
            "paragraph",
            "Can I change this section? Yes. The builder detects edits and will report a conflict instead of overwriting your changes. Keep the local state manifest for reliable reruns.",
        ),
        block("divider"),
        block(
            "paragraph",
            f"Template guide v{VERSION} • Review the setup checklist before sharing or selling. Built with Notion Template Builder.",
        ),
    ]
    root = block("callout", children=blocks, icon={"type": "emoji", "emoji": spec.icon})
    root["callout"]["rich_text"] = [
        rich(f"{spec.icon} {spec.title} · Start here"),
        rich(f"  [{marker}]", code=True, color="gray"),
    ]
    return root


def content_hash(block):
    return digest(signature(block))

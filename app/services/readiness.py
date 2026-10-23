"""Reports distinguish implemented calculations from manual workflow configuration."""

from app.templates.catalog import SPECS, VERSION


def readiness(plan, applied=False, verified=False):
    lines = [
        "# Commercial readiness report",
        "",
        f"Version: {VERSION}",
        f"Applied in Notion: {applied}",
        f"Verified by fresh inventory and plan: {verified}",
        "",
        "No pages, databases or records are created or deleted. Original starter content is preserved.",
        "The managed guide is appended to each existing page; original layout remains visible.",
        (
            "Missing functionality: live cross-database balances, automatic analytics imports, "
            "relations/rollups and automatic notifications are not implemented."
        ),
        "No automatic rollback, public sharing, duplication or publishing is configured.",
        "",
    ]
    for key in plan["templates"]:
        spec = SPECS[key]
        lines += [
            f"## {spec.title}",
            "",
            "### Included in this upgrade",
            "",
            "- Welcome, quick start, feature overview, live database links, sample workflow, customization help, FAQ and version information.",
        ]
        for database, formulas in spec.formulas.items():
            lines += [f"- {database}: {formula.name}" for formula in formulas]
        for database, properties in spec.properties.items():
            lines += [f"- {database}: additional fields " + ", ".join(properties)]
        if spec.prompts:
            lines += ["- Reusable AI prompts for hooks, scripts, titles, descriptions and ideas."]
        lines += ["", "### Manual setup and usability review", ""]
        lines += [f"- {item}" for item in spec.manual]
        lines += [
            "",
            "### Publishing checklist",
            "",
            "- Review every formula with representative real and empty inputs.",
            "- Review starter examples; remove private information from a separate sales copy.",
            "- Configure views and formatting, then test the buyer's first-run experience.",
            "- Review mobile layout and move the managed guide higher on the page if desired.",
            "- Prepare support details, license terms, product screenshots and duplication instructions.",
            "- Enable sharing and duplication manually only after final review.",
            "",
        ]
    if plan["issues"]:
        lines += ["## Blocking issues", ""] + plan["issues"]
    return "\n".join(lines) + "\n"

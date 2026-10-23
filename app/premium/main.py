"""Premium edition runner. Dry-run is the default; apply uses a saved fresh backup."""

import json
from pathlib import Path

import typer

from app.config import Settings
from app.notion.client import NotionError
from app.premium.catalog import BRANDS, FIELDS, FORMULAS, RELATIONS, ROLLUPS
from app.premium.client import PremiumClient
from app.premium.help import update_help
from app.premium.upgrade import PremiumUpgrade
from app.premium.views import DASHBOARDS
from app.services.state import save_json


def main(apply: bool = False, yes: bool = False):
    counts = {
        "new_inputs": sum(len(fields) for tables in FIELDS.values() for fields in tables.values()),
        "relations": sum(len(relations) for relations in RELATIONS.values()),
        "formulas": sum(len(fields) for tables in FORMULAS.values() for fields in tables.values()),
        "rollups": sum(len(fields) for tables in ROLLUPS.values() for fields in tables.values()),
        "dashboards": len(DASHBOARDS),
        "working_views": sum(
            sum(len(group) for group in spec["groups"]) + len(spec["tabs"])
            for spec in DASHBOARDS.values()
        ),
        "banners": len(BRANDS),
    }
    print("Premium v2 scope:", counts, flush=True)
    print(
        "Native dashboard views require Notion Business. API acceptance does not confirm rendered availability. Client Desk has a separate ordinary-view home.",
        flush=True,
    )
    if not apply:
        print(
            "Dry-run. Existing records/pages/data sources will not be recreated. Use --apply to execute."
        )
        return
    if not yes:
        typer.confirm("Apply the premium redesign using the completed backup?", abort=True)
    from app.main import upgrade_lock

    client = None
    try:
        with upgrade_lock():
            pointer = json.loads(Path("state/premium-v2-backup.json").read_text(encoding="utf-8"))
            path = Path(pointer["path"])
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            if not snapshot["inventory"]["complete"]:
                raise ValueError("Backup inventory is incomplete.")
            settings = Settings.load()
            if (
                snapshot["inventory"]["parent"]["id"].replace("-", "")
                != settings.parent_page_id.hex
            ):
                raise ValueError("Backup belongs to a different workspace parent.")
            client = PremiumClient(settings)
            upgrade = PremiumUpgrade(client, snapshot, path)
            upgrade.schemas()
            upgrade.migrate()
            upgrade.banners()
            upgrade.dashboards()
            upgrade.workspaces()
            update_help(upgrade)
            verification = upgrade.verify()
            report = {
                "version": "2.0.0",
                "rendered_ui_verified": False,
                "backup": str(path),
                "verified": verification,
                "issues": upgrade.state["issues"],
                "scope": counts,
                "limitations": [
                    "Native button actions and recurring database templates require Notion UI configuration; no fake buttons were created.",
                    "No bank, YouTube, email or invoice-sending integration is enabled.",
                    "All existing page IDs, data sources and original record values are preserved.",
                    "Native chart availability depends on the workspace plan; rejected optional charts are listed in issues.",
                ],
            }
            save_json("reports/premium-v2-result.json", report)
            print(
                "API configuration verified; rendered UI still requires checking:",
                verification,
                flush=True,
            )
            print("Items for review:", len(upgrade.state["issues"]), flush=True)
    except (NotionError, ValueError, OSError) as exc:
        # Configuration validation can include input values; keep its output generic.
        if isinstance(exc, NotionError):
            print(str(exc), flush=True)
        else:
            print("Premium upgrade stopped:", type(exc).__name__, flush=True)
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    typer.run(main)

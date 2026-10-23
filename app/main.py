"""Discover, plan, back up and safely upgrade existing Notion templates."""

import json
from pathlib import Path

import typer
from rich.console import Console

from app.config import Settings
from app.notion.client import NotionClient
from app.notion.discovery import discover as discover_resources
from app.notion.discovery import markdown_report

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def discover(output: Path = Path("reports")):
    """Read existing resources and write local JSON, Markdown and ID state."""
    try:
        settings = Settings.load()
    except ValueError:
        console.print(
            "Configuration invalid. Set NOTION_API_TOKEN and a valid "
            "NOTION_PARENT_PAGE_ID in .env.",
            markup=False,
        )
        raise typer.Exit(1) from None
    client = NotionClient(settings)
    try:
        inventory = discover_resources(client, str(settings.parent_page_id), settings.api_version)
    finally:
        client.close()
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(inventory.model_dump_json(indent=2), encoding="utf-8")
    (output / "inventory.md").write_text(markdown_report(inventory), encoding="utf-8")
    state = {
        "version": 1,
        "generated_at": inventory.generated_at,
        "complete": inventory.complete,
        "templates": {
            key: {"page_id": entry.get("page", {}).get("id"), "status": entry["status"]}
            for key, entry in inventory.templates.items()
        },
    }
    Path("state").mkdir(exist_ok=True)
    temp = Path("state/discovery.tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace("state/discovery.json")
    console.print(
        f"Inventory saved to {output.resolve()}; complete={inventory.complete}", markup=False
    )
    if not inventory.complete:
        console.print("Some resources are missing, ambiguous or inaccessible. See inventory.md.")
        raise typer.Exit(2)


@app.callback()
def main():
    """Notion Template Builder: additive upgrades with backups and dry-run defaults."""


# Upgrade tools use an explicitly separate client from the original GET-only discovery transport.
from contextlib import contextmanager, nullcontext

from app.notion.client import NotionError
from app.notion.upgrades import UpgradeClient
from app.services.backup import backup as create_backup
from app.services.readiness import readiness
from app.services.state import load_manifest, save_json
from app.services.upgrade import apply_plan
from app.services.validation import build_plan, plan_markdown
from app.templates.catalog import SPECS


def selected_keys(template):
    if template == "all":
        return list(SPECS)
    if template not in SPECS:
        raise ValueError(
            "Unknown template. Choose all, finance, student, creator, habits or freelancer."
        )
    return [template]


def connect_upgrade():
    settings = Settings.load()
    return settings, UpgradeClient(settings)


def prepare(client, settings, keys):
    inventory = discover_resources(client, str(settings.parent_page_id), settings.api_version)
    manifest = load_manifest()
    plan = build_plan(client, inventory, keys, manifest)
    return inventory, manifest, plan


def save_plan(plan):
    save_json("reports/upgrade-plan.json", plan)
    Path("reports/upgrade-plan.md").write_text(plan_markdown(plan), encoding="utf-8")
    Path("reports/commercial-readiness-plan.md").write_text(readiness(plan), encoding="utf-8")


def summary(plan):
    for operation in plan["operations"]:
        label = f"{operation['template']}: {operation['kind']}"
        if operation["kind"] == "schema":
            label += f" / {operation['database']} / " + ", ".join(operation["properties"])
        console.print(label, markup=False)
    for issue in plan["issues"]:
        console.print("CONFLICT: " + issue, markup=False)
    console.print(f"{len(plan['operations'])} operations, {len(plan['issues'])} conflicts.")


@contextmanager
def upgrade_lock():
    path = Path("state/upgrade.lock")
    path.parent.mkdir(exist_ok=True)
    try:
        handle = path.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError(
            "An upgrade lock exists. Check that no upgrade is running before removing it."
        ) from None
    try:
        handle.write("Upgrade in progress. Do not run another apply.\n")
        handle.close()
        yield
    finally:
        handle.close()
        path.unlink(missing_ok=True)


@app.command("plan")
def plan_command(template: str = "all"):
    """Read Notion and save proposed changes; never mutate Notion or the manifest."""
    client = None
    try:
        settings, client = connect_upgrade()
        _, _, plan = prepare(client, settings, selected_keys(template))
        save_plan(plan)
        summary(plan)
        if plan["issues"]:
            raise typer.Exit(2)
    except (ValueError, NotionError, OSError):
        console.print("Planning failed. Check configuration, permissions and local state.")
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()


@app.command("validate")
def validate_command(template: str = "all"):
    """Validate discovery, property types, formula inputs and ownership."""
    plan_command(template)


@app.command("backup")
def backup_command(template: str = "all"):
    """Save accessible metadata, blocks, schemas and records locally."""
    client = None
    try:
        settings, client = connect_upgrade()
        inventory = discover_resources(client, str(settings.parent_page_id), settings.api_version)
        path, _ = create_backup(client, inventory, selected_keys(template))
        console.print(f"Snapshot saved: {path.resolve()}", markup=False)
    except (ValueError, NotionError, OSError):
        console.print("Backup failed; no Notion content was changed.")
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()


@app.command("upgrade")
def upgrade_command(template: str = "all", apply: bool = False, yes: bool = False):
    """Dry-run by default. --apply backs up before writes; --yes confirms the displayed plan."""
    client = None
    try:
        with upgrade_lock() if apply else nullcontext():
            keys = selected_keys(template)
            settings, client = connect_upgrade()
            inventory, manifest, plan = prepare(client, settings, keys)
            save_plan(plan)
            summary(plan)
            if plan["issues"]:
                console.print("No changes applied. Resolve conflicts in reports/upgrade-plan.md.")
                raise typer.Exit(2)
            if not apply:
                console.print("Dry-run only. Use --apply to back up and apply these changes.")
                return
            if not plan["operations"]:
                console.print("Already up to date. No changes needed.")
                return
            if not yes:
                typer.confirm("Back up and apply this plan to the existing templates?", abort=True)
            path, _ = create_backup(client, inventory, keys)
            save_json(path.with_suffix(".plan.json"), plan)
            console.print(f"Backup saved: {path.resolve()}", markup=False)
            results = apply_plan(client, plan, manifest, path)
            save_json("reports/last-upgrade.json", {"backup": str(path), "operations": results})
            _, _, verification = prepare(client, settings, keys)
            verified = not verification["issues"] and not verification["operations"]
            Path("reports/commercial-readiness.md").write_text(
                readiness(plan, applied=True, verified=verified), encoding="utf-8"
            )
            save_json("reports/verification.json", verification)
            if not verified:
                console.print(
                    "Writes completed but verification needs review. See reports/verification.json."
                )
                raise typer.Exit(2)
            console.print("Upgrade applied and verified. A repeat run requires no changes.")
    except (ValueError, NotionError, OSError) as exc:
        # Transport errors are sanitized. Never print configuration-validation input values.
        if isinstance(exc, NotionError):
            console.print(str(exc), markup=False)
        else:
            console.print(
                "Upgrade stopped. Check configuration, plan, backup and manifest before retrying."
            )
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()


@app.command("status")
def status_command():
    """Show local upgrade state without contacting Notion."""
    try:
        manifest = load_manifest()
        for key in SPECS:
            managed = manifest["dashboards"].get(key, {})
            console.print(f"{key}: {managed.get('status', 'not upgraded')}")
        console.print("Local observations only; run plan to verify against Notion.")
    except (ValueError, OSError):
        console.print("Cannot read the local manifest.")
        raise typer.Exit(1) from None


@app.command("premium")
def premium_command(apply: bool = False, yes: bool = False):
    """Preview or apply the journaled premium v2 redesign."""
    from app.premium.main import main as premium_main

    premium_main(apply=apply, yes=yes)


if __name__ == "__main__":
    app()

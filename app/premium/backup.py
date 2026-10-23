"""Create a premium snapshot, retaining the recovery pointer once an upgrade exists."""

from pathlib import Path

from app.config import Settings
from app.notion.discovery import discover
from app.premium.client import PremiumClient
from app.services.backup import backup
from app.services.state import save_json


def main():
    settings = Settings.load()
    client = PremiumClient(settings)
    try:
        inventory = discover(client, str(settings.parent_page_id), settings.api_version)
        if not inventory.complete:
            raise ValueError("Incomplete inventory; snapshot pointer was not changed.")
        path, snapshot = backup(client, inventory, list(inventory.templates))
        snapshot["views"] = {}
        for database_id in snapshot["databases"]:
            snapshot["views"][database_id] = [
                client.get(f"views/{reference['id']}")
                for reference in client.list_views(database_id)
            ]
        save_json(path, snapshot)
        if not Path("state/premium-v2.json").exists():
            save_json("state/premium-v2-backup.json", {"path": str(path)})
        print(f"Snapshot saved: {path}")
        print("Existing premium recovery pointers, if any, were preserved.")
    finally:
        client.close()


if __name__ == "__main__":
    main()

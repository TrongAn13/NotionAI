"""Prevent the plan gate and imported-select usability regressions."""

from copy import deepcopy

from app.premium.client_desk import lifecycle_choices, modules
from app.premium.views import compile_view


def test_home_has_no_business_dashboard_or_chart():
    specs = [spec for _, _, _, group in modules() for spec in group]
    assert len(specs) == 12
    assert {spec["type"] for spec in specs} <= {"table", "list", "gallery", "board", "calendar"}


def test_invoice_title_precedes_receipt_fields_regardless_of_schema_order():
    schema = {
        "id": "source",
        "properties": {
            "Balance": {"id": "balance", "type": "number"},
            "Hidden": {"id": "hidden", "type": "rich_text"},
            "Invoice": {"id": "title", "type": "title"},
            "Due": {"id": "due", "type": "date"},
        },
    }
    spec = {
        "db": "Invoices",
        "name": "Unpaid",
        "type": "table",
        "columns": ["Invoice", "Due", "Balance"],
    }
    result = compile_view(spec, schema, "blue")
    assert result["configuration"]["properties"] == [
        {"property_id": "title", "visible": True},
        {"property_id": "due", "visible": True},
        {"property_id": "balance", "visible": True},
        {"property_id": "hidden", "visible": False},
    ]


def test_lifecycle_choices_keep_existing_ids_and_custom_options_and_replay():
    class Upgrade:
        def __init__(self):
            self.tables = {"freelancer": {}}
            self.writes = []
            self.client = self
            for table, fields in {
                "Tasks": ["Status", "Priority"],
                "Projects": ["Status"],
                "Leads": ["Stage"],
                "Invoices": ["Payment Status"],
                "Clients": ["Stage"],
            }.items():
                self.tables["freelancer"][table] = {
                    "id": table,
                    "properties": {
                        field: {
                            "type": "select",
                            "select": {
                                "options": [
                                    {
                                        "id": "custom-id",
                                        "name": "Custom workflow",
                                        "color": "purple",
                                    }
                                ]
                            },
                        }
                        for field in fields
                    },
                }

        def refresh(self, key, table):
            return self.tables[key][table]

        def operation(self, key, payload, function, recover=None):
            return function()

        def mutate(self, method, path, payload):
            self.writes.append(deepcopy(payload))
            table = path.split("/")[-1]
            for field, spec in payload["properties"].items():
                self.tables["freelancer"][table]["properties"][field]["select"] = spec["select"]
            return self.tables["freelancer"][table]

    upgrade = Upgrade()
    lifecycle_choices(upgrade)
    writes = len(upgrade.writes)
    assert writes == 5
    for source in upgrade.tables["freelancer"].values():
        for prop in source["properties"].values():
            assert prop["select"]["options"][0] == {
                "id": "custom-id",
                "name": "Custom workflow",
                "color": "purple",
            }
    assert "Done" in {
        o["name"]
        for o in upgrade.tables["freelancer"]["Tasks"]["properties"]["Status"]["select"]["options"]
    }
    lifecycle_choices(upgrade)
    assert len(upgrade.writes) == writes

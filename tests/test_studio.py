"""Regression checks for dependency order, scoped capture and editable content."""

import re

from app.premium.studio import add_schemas, change_views
from app.premium.studio_content import project_kit, to_html
from app.premium.views import compile_view


def test_formula_dependencies_exist_before_each_schema_patch():
    class Upgrade:
        def __init__(self):
            self.fields = {"Tasks": {"Remaining Task"}, "Projects": {"Task Entries", "Status"}}

        def ensure_fields(self, key, table, fields, stage):
            for name, spec in fields.items():
                if "formula" in spec:
                    references = set(
                        re.findall(r'prop\("([^"]+)"\)', spec["formula"]["expression"])
                    )
                    assert references <= self.fields[table], (name, references - self.fields[table])
                if "rollup" in spec:
                    assert spec["rollup"]["relation_property_name"] in self.fields[table]
                    assert spec["rollup"]["rollup_property_name"] in self.fields["Tasks"]
            self.fields[table].update(fields)

    add_schemas(Upgrade())


def test_every_project_change_view_keeps_project_and_work_type_filters():
    for spec in change_views("project-123"):
        assert {"property": "Project Link", "relation": {"contains": "project-123"}} in spec[
            "filter"
        ]["and"]
        assert {"property": "Work Type", "select": {"equals": "Change request"}} in spec["filter"][
            "and"
        ]
        names = list(dict.fromkeys([*spec["columns"], "Work Type"]))
        schema = {
            "id": "tasks",
            "properties": {
                name: {"id": name, "type": "title" if name == "Task" else "rich_text"}
                for name in names
            },
        }
        assert compile_view(spec, schema, "blue")["filter"] == spec["filter"]


def test_clipboard_html_escapes_document_text():
    blocks = [
        {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": '<script>alert("x")</script>'}}]},
        }
    ]
    assert "<script>" not in to_html(blocks)
    assert "&lt;script&gt;" in to_html(blocks)
    kit = project_kit("https://example.com/marker")
    assert len([b for b in kit if b["type"] == "toggle"]) == 6

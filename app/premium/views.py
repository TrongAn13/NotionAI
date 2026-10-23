"""Native dashboard widgets and capture tabs over the existing data sources."""


def view(db, name, kind="table", columns=(), *, filter=None, sort=None, group=None, date=None):
    result = {"db": db, "name": name, "type": kind, "columns": list(columns)}
    if filter:
        result["filter"] = filter
    if sort:
        result["sorts"] = [{"property": sort, "direction": "ascending"}]
    if group:
        result["group"] = group
    if date:
        result["date"] = date
    return result


def number(db, name, prop=None, filter=None):
    result = view(db, name, "chart", filter=filter)
    result["aggregation"] = (
        {"aggregator": "sum", "property_id": prop} if prop else {"aggregator": "count"}
    )
    result["optional"] = True
    return result


def eq(prop, value):
    return {"property": prop, "select": {"equals": value}}


def formula_string(prop, value):
    return {"property": prop, "formula": {"string": {"equals": value}}}


def formula_gt(prop, value):
    return {"property": prop, "formula": {"number": {"greater_than": value}}}


MONTH = {"property": "In Current Month", "formula": {"checkbox": {"equals": True}}}
# Date filters below use Notion's relative conditions so they continue working after duplication.

DASHBOARDS = {
    "finance": {
        "primary": "Transactions",
        "groups": [
            [
                number("Transactions", "Income this month", "Recorded Income", MONTH),
                number("Transactions", "Expenses this month", "Recorded Expense", MONTH),
                number("Monthly Budgets", "Budget left this month", "Live Budget Left", MONTH),
            ],
            [
                view("Accounts", "Your accounts", "gallery", ["Recorded Balance", "Currency"]),
                view(
                    "Savings Goals",
                    "Build your safety net",
                    "gallery",
                    ["Goal Progress", "Target Amount", "Target Date"],
                ),
            ],
            [
                view(
                    "Monthly Budgets",
                    "Monthly budget desk",
                    columns=[
                        "Month",
                        "Category",
                        "Budget",
                        "Linked Spending",
                        "Live Budget Left",
                        "Budget Progress",
                        "Budget Signal",
                    ],
                    sort="Month Start",
                )
            ],
            [
                view(
                    "Transactions",
                    "Recent movements",
                    columns=["Name", "Date", "Flow Kind", "Amount", "Account Link", "Budget Link"],
                    sort="Date",
                )
            ],
        ],
        "tabs": [
            view(
                "Transactions",
                "Record a movement",
                columns=[
                    "Name",
                    "Date",
                    "Movement Kind",
                    "Type",
                    "Amount",
                    "Category",
                    "Account Link",
                    "Transfer Destination",
                    "Budget Link",
                    "Notes",
                ],
            ),
            view(
                "Transactions",
                "Match your accounts",
                columns=["Name", "Account", "Account Link", "Amount"],
                filter={"property": "Account Link", "relation": {"is_empty": True}},
            ),
            view(
                "Transactions",
                "This month",
                columns=["Name", "Date", "Recorded Income", "Recorded Expense", "Budget Link"],
                filter=MONTH,
            ),
            view(
                "Monthly Budgets",
                "Monthly review",
                columns=["Month", "Category", "Budget Signal", "Linked Spending", "Review Notes"],
                sort="Month Start",
            ),
            view(
                "Transactions",
                "All records",
                columns=["Name", "Date", "Amount", "Type", "Account", "Account Link"],
            ),
        ],
    },
    "student": {
        "primary": "Assignments",
        "groups": [
            [
                number("Assignments", "Open study hours", "Remaining Hours"),
                number("Courses", "Current courses"),
            ],
            [
                view(
                    "Courses",
                    "Your course studio",
                    "gallery",
                    [
                        "Semester",
                        "Course Completion",
                        "Current Graded Average",
                        "Weekly Workload",
                        "Open Study Hours",
                    ],
                )
            ],
            [
                view(
                    "Assignments",
                    "What needs attention",
                    columns=[
                        "Task",
                        "Course Link",
                        "Due Date",
                        "Priority",
                        "Deadline Signal",
                        "Remaining Hours",
                    ],
                    filter={"property": "Done Unit", "formula": {"number": {"equals": 0}}},
                    sort="Due Date",
                )
            ],
            [
                view(
                    "Exams",
                    "Exam room",
                    "calendar",
                    ["Exam", "Course Link", "Revision Focus", "Readiness"],
                    date="Date",
                ),
                view(
                    "Study Sessions",
                    "Study and revision",
                    "list",
                    ["Date", "Course Link", "Topic", "Confidence"],
                    sort="Date",
                ),
            ],
        ],
        "tabs": [
            view(
                "Assignments",
                "Assignment desk",
                columns=[
                    "Task",
                    "Course Link",
                    "Due Date",
                    "Priority",
                    "Estimated Hours",
                    "Status",
                ],
            ),
            view(
                "Assignments",
                "Deadline calendar",
                "calendar",
                ["Course Link", "Priority", "Status"],
                date="Due Date",
            ),
            view(
                "Assignments",
                "Grade planning",
                columns=[
                    "Task",
                    "Course Link",
                    "Graded",
                    "Points Earned",
                    "Points Possible",
                    "Weight %",
                    "Weighted Points",
                ],
            ),
            view(
                "Courses",
                "Weekly workload",
                columns=[
                    "Course",
                    "Weekly Study Capacity",
                    "Open Study Hours",
                    "Weekly Workload",
                    "Current Graded Average",
                ],
            ),
            view(
                "Study Sessions",
                "Plan a study session",
                columns=[
                    "Session",
                    "Course Link",
                    "Date",
                    "Duration Minutes",
                    "Topic",
                    "Review On",
                    "Focus Outcome",
                    "Confidence",
                ],
            ),
        ],
    },
    "creator": {
        "primary": "Production Pipeline",
        "groups": [
            [
                number("Production Pipeline", "Video projects"),
                number("Performance", "Recorded views", "Views"),
            ],
            [
                view(
                    "Production Pipeline",
                    "Production floor",
                    "board",
                    ["Channel Link", "Target Date", "Production Focus", "Release Check"],
                    group="Production Stage",
                )
            ],
            [
                view(
                    "Production Pipeline",
                    "Unblock the next release",
                    "list",
                    ["Target Date", "Blocker", "Owner", "Next Action"],
                    filter={"property": "Blocker", "rich_text": {"is_not_empty": True}},
                ),
                view("Channels", "Channel rooms", "gallery", ["Platform", "Niche", "Status"]),
            ],
            [
                view(
                    "Publishing Calendar",
                    "Release calendar",
                    "calendar",
                    ["Channel Link", "Production Link", "Status"],
                    date="Publish Date",
                )
            ],
        ],
        "tabs": [
            view(
                "Ideas",
                "Capture an idea",
                columns=[
                    "Idea",
                    "Channel Link",
                    "Audience Problem",
                    "Hook",
                    "Pillar",
                    "Research Needed",
                    "Effort Hours",
                    "Priority",
                ],
            ),
            view(
                "Production Pipeline",
                "Packaging lab",
                columns=[
                    "Video",
                    "Audience Promise",
                    "Title A",
                    "Title B",
                    "Thumbnail Brief",
                    "Thumbnail A",
                    "Thumbnail B",
                    "Packaging Check",
                ],
            ),
            view(
                "Production Pipeline",
                "Repurpose map",
                columns=[
                    "Video",
                    "Channel Link",
                    "Repurpose Of",
                    "Derivatives",
                    "Production Stage",
                ],
            ),
            view(
                "Performance",
                "Learning log",
                columns=[
                    "Video",
                    "Production Link",
                    "Snapshot On",
                    "Window",
                    "Views",
                    "NTB Engagement Rate",
                    "CTR %",
                    "Result Notes",
                    "Next Experiment",
                    "Learning Status",
                ],
            ),
            view(
                "Production Pipeline",
                "Production details",
                columns=[
                    "Video",
                    "Channel Link",
                    "Production Stage",
                    "Script Draft",
                    "Hook Draft",
                    "Research Notes",
                    "Next Action",
                    "Target Date",
                ],
            ),
        ],
    },
    "habits": {
        "primary": "Habits",
        "groups": [
            [
                number(
                    "Habit Log",
                    "Full actions — last week",
                    "Full Credit",
                    {"property": "Date", "date": {"past_week": {}}},
                ),
                number(
                    "Habit Log",
                    "Minimum actions — last week",
                    "Minimum Credit",
                    {"property": "Date", "date": {"past_week": {}}},
                ),
            ],
            [
                view(
                    "Habits",
                    "Your daily practice",
                    "gallery",
                    ["Seven Day Rhythm", "Full Version", "Minimum Version", "Restart Cue"],
                )
            ],
            [
                view(
                    "Habit Log",
                    "Today and the next small action",
                    columns=[
                        "Entry",
                        "Habit Link",
                        "Date",
                        "Completion Mode",
                        "Completed",
                        "Notes",
                    ],
                    filter={"property": "Is Today", "formula": {"checkbox": {"equals": True}}},
                )
            ],
            [
                view(
                    "Habit Log",
                    "Your rhythm",
                    "calendar",
                    ["Habit Link", "Rhythm Label"],
                    date="Date",
                ),
                view(
                    "Weekly Review",
                    "Weekly reset",
                    "list",
                    ["Energy", "One Small Win", "Friction", "Adjustment"],
                ),
            ],
        ],
        "tabs": [
            view(
                "Habit Log",
                "Log a small win",
                columns=["Entry", "Habit Link", "Date", "Completion Mode", "Planned", "Notes"],
            ),
            view(
                "Habits",
                "Minimum day plans",
                columns=[
                    "Habit",
                    "Full Version",
                    "Minimum Version",
                    "Cue",
                    "Restart Plan",
                    "Goal Per Week",
                ],
            ),
            view(
                "Habit Log",
                "Weekly log",
                columns=[
                    "Entry",
                    "Date",
                    "Habit Link",
                    "Rhythm Label",
                    "Full Credit",
                    "Minimum Credit",
                ],
                filter={"property": "Date", "date": {"past_week": {}}},
            ),
            view(
                "Goals",
                "Goal review",
                "gallery",
                ["Target Date", "Status", "NTB Goal Progress", "Habit Entries"],
            ),
        ],
    },
    "freelancer": {
        "primary": "Projects",
        "groups": [
            [
                number("Invoices", "Outstanding balance", "Outstanding Balance"),
                number("Invoices", "Recorded receipts", "Recorded Receipts"),
                number("Invoices", "Overdue balance", "Overdue Balance"),
            ],
            [
                view(
                    "Projects",
                    "Delivery studio",
                    "gallery",
                    [
                        "Client Link",
                        "Due Date",
                        "Delivery Progress",
                        "Scope Signal",
                        "Hours Signal",
                    ],
                )
            ],
            [
                view(
                    "Tasks",
                    "Your next deliveries",
                    columns=[
                        "Task",
                        "Project Link",
                        "Due Date",
                        "Priority",
                        "Status",
                        "Hours Logged",
                    ],
                    filter={"property": "Remaining Task", "formula": {"number": {"equals": 1}}},
                    sort="Due Date",
                ),
                view(
                    "Leads",
                    "Client pipeline",
                    "board",
                    ["Service", "Next Follow Up", "Estimated Value"],
                    group="Stage",
                ),
            ],
            [
                view(
                    "Invoices",
                    "Payments requiring attention",
                    columns=[
                        "Invoice",
                        "Client Link",
                        "Due Date",
                        "Outstanding Balance",
                        "Receipt State",
                        "Overdue Balance",
                    ],
                    filter=formula_gt("Outstanding Balance", 0),
                    sort="Due Date",
                )
            ],
        ],
        "tabs": [
            view(
                "Projects",
                "Scope guard",
                columns=[
                    "Project",
                    "Scope Notes",
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
                    "Costs Reviewed",
                ],
            ),
            view(
                "Invoices",
                "Record a payment",
                columns=[
                    "Invoice",
                    "Client Link",
                    "Project Link",
                    "Amount",
                    "Amount Received",
                    "Payment Status",
                    "Outstanding Balance",
                    "Due Date",
                ],
            ),
            view(
                "Clients",
                "Client rooms",
                "gallery",
                ["Company", "Email", "Stage", "Outstanding Invoices"],
            ),
            view(
                "Tasks",
                "Delivery calendar",
                "calendar",
                ["Project Link", "Priority", "Status"],
                date="Due Date",
            ),
        ],
    },
}


def compile_view(spec, schema, color):
    """Resolve human-facing field names to current Notion property IDs."""
    kind = spec["type"]
    properties = schema["properties"]

    def pid(name):
        if name not in properties:
            raise ValueError(f"Missing view field: {spec['db']}/{name}")
        return properties[name]["id"]

    config = {"type": kind}
    if kind == "chart":
        value = dict(spec["aggregation"])
        if "property_id" in value:
            value["property_id"] = pid(value["property_id"])
        config.update(chart_type="number", value=value, color_theme=color, height="small")
    else:
        requested = set(spec["columns"])
        # Order matters: Notion renders the array as the visible column order.
        # CSV schema order can put the page title after every numeric field.
        ordered = [name for name, p in properties.items() if p["type"] == "title"]
        ordered += [name for name in spec["columns"] if name not in ordered]
        ordered += [name for name in properties if name not in ordered]
        config["properties"] = [
            {
                "property_id": properties[name]["id"],
                "visible": name in requested or properties[name]["type"] == "title",
            }
            for name in ordered
        ]
        if kind in ("board", "gallery"):
            config.update(cover={"type": "page_cover"}, cover_size="medium", cover_aspect="cover")
        if kind == "board":
            name = spec["group"]
            config["group_by"] = {
                "type": properties[name]["type"],
                "property_id": pid(name),
                "sort": {"type": "manual"},
            }
            if properties[name]["type"] == "status":
                config["group_by"]["group_by"] = "option"
        if kind == "calendar":
            config.update(
                date_property_id=pid(spec["date"]), view_range="month", show_weekends=True
            )
    result = {
        "data_source_id": schema["id"],
        "name": spec["name"],
        "type": kind,
        "configuration": config,
    }
    if "filter" in spec:
        result["filter"] = spec["filter"]
    if "sorts" in spec:
        result["sorts"] = spec["sorts"]
    return result


# Prevent summing overlapping performance snapshots as channel-level views.
DASHBOARDS["creator"]["groups"][0][1] = number(
    "Performance", "Snapshots to review", filter=formula_string("Learning Status", "Review pending")
)
DASHBOARDS["finance"]["groups"][3][0]["sorts"][0]["direction"] = "descending"

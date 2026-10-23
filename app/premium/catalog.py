"""Premium v2 data model: additive fields, explicit relations and live calculations."""

from app.templates.base import number, select, text

BRANDS = {
    "finance": (
        "Clarity Money",
        "Know your month. Give your money a clear direction.",
        "💰",
        "green",
    ),
    "student": ("Semester Studio", "See the next deadline. Make room to learn.", "🎓", "purple"),
    "creator": (
        "Channel Studio",
        "Shape the idea. Ship the video. Learn what works.",
        "🎬",
        "orange",
    ),
    "habits": ("Momentum", "Small wins, honest progress and room to restart.", "🌱", "yellow"),
    "freelancer": (
        "Client Desk",
        "Deliver with clarity. Keep scope and payments in view.",
        "💼",
        "blue",
    ),
}

FIELDS = {
    "finance": {
        "Transactions": {
            "Movement Kind": select("Income", "Expense", "Transfer"),
            "Goal Contribution": number(),
        },
        "Monthly Budgets": {"Month Start": {"date": {}}, "Review Notes": text()},
        "Savings Goals": {"Next Contribution": text()},
    },
    "student": {
        "Assignments": {
            "Points Earned": number(),
            "Points Possible": number(),
            "Weight %": number(),
            "Graded": {"checkbox": {}},
        },
        "Courses": {"Weekly Study Capacity": number(), "Course Objective": text()},
        "Exams": {
            "Revision Focus": text(),
            "Readiness": select("Not Started", "Practicing", "Ready"),
        },
        "Study Sessions": {
            "Focus Outcome": text(),
            "Confidence": select("Low", "Building", "Ready"),
            "Review On": {"date": {}},
        },
    },
    "creator": {
        "Production Pipeline": {
            "Audience Promise": text(),
            "Hook Draft": text(),
            "Research Notes": text(),
            "Thumbnail Brief": text(),
            "Thumbnail A": {"files": {}},
            "Thumbnail B": {"files": {}},
            "Title A": text(),
            "Title B": text(),
            "Blocker": text(),
            "Owner": {"people": {}},
            "Next Action": text(),
        },
        "Performance": {
            "Snapshot On": {"date": {}},
            "Window": select("7 days", "28 days", "Lifetime"),
            "Impressions": number(),
            "CTR %": number(),
            "Average View Minutes": number(),
            "Working Hypothesis": text(),
            "Result Notes": text(),
            "Next Experiment": text(),
        },
        "Ideas": {"Audience Problem": text(), "Research Needed": text(), "Effort Hours": number()},
    },
    "habits": {
        "Habits": {
            "Full Version": text(),
            "Minimum Version": text(),
            "Cue": text(),
            "Restart Plan": text(),
        },
        "Habit Log": {
            "Completion Mode": select("Full", "Minimum", "Skipped", "Rest"),
            "Planned": {"checkbox": {}},
        },
        "Weekly Review": {
            "Energy": select("High", "Balanced", "Low"),
            "Friction": text(),
            "Adjustment": text(),
            "One Small Win": text(),
        },
    },
    "freelancer": {
        "Projects": {
            "Included Revisions": number(),
            "Revisions Used": number(),
            "Scope Notes": text(),
            "Change Request": text(),
            "Hours Budget": number(),
            "Direct Costs": number(),
            "Costs Reviewed": {"checkbox": {}},
        },
        "Tasks": {
            "Hours Logged": number(),
            "Scope Change": {"checkbox": {}},
            "Change Description": text(),
        },
        "Invoices": {"Amount Received": number()},
    },
}

# source database, source relation name, target database, inverse name, legacy match field
RELATIONS = {
    "finance": [
        ("Transactions", "Account Link", "Accounts", "Account Entries", "Account"),
        ("Transactions", "Budget Link", "Monthly Budgets", "Budget Entries", None),
        ("Transactions", "Transfer Destination", "Accounts", "Incoming Transfers", None),
        ("Transactions", "Savings Goal Link", "Savings Goals", "Contribution Entries", None),
    ],
    "student": [
        ("Assignments", "Course Link", "Courses", "Assignment Entries", "Course"),
        ("Exams", "Course Link", "Courses", "Exam Entries", "Course"),
        ("Study Sessions", "Course Link", "Courses", "Study Entries", "Course"),
    ],
    "creator": [
        ("Ideas", "Channel Link", "Channels", "Idea Entries", "Channel"),
        ("Production Pipeline", "Channel Link", "Channels", "Video Entries", "Channel"),
        ("Publishing Calendar", "Channel Link", "Channels", "Release Entries", "Channel"),
        ("Production Pipeline", "Idea Link", "Ideas", "Production Projects", None),
        (
            "Publishing Calendar",
            "Production Link",
            "Production Pipeline",
            "Release Entries",
            "Post",
        ),
        ("Performance", "Production Link", "Production Pipeline", "Performance Entries", "Video"),
        ("Production Pipeline", "Repurpose Of", "Production Pipeline", "Derivatives", None),
    ],
    "habits": [
        ("Habit Log", "Habit Link", "Habits", "Habit Entries", "Habit"),
        ("Habits", "Goal Link", "Goals", "Habit Entries", None),
    ],
    "freelancer": [
        ("Projects", "Client Link", "Clients", "Project Entries", "Client"),
        ("Tasks", "Project Link", "Projects", "Task Entries", "Project"),
        ("Invoices", "Client Link", "Clients", "Invoice Entries", "Client"),
        ("Invoices", "Project Link", "Projects", "Invoice Entries", "Project"),
        ("Leads", "Client Link", "Clients", "Lead Entries", None),
    ],
}

FORMULAS = {
    "finance": {
        "Transactions": {
            "Flow Kind": 'if(empty(prop("Movement Kind")), prop("Type"), prop("Movement Kind"))',
            "Signed Movement": 'if(prop("Flow Kind") == "Income", abs(prop("Amount")), if(or(prop("Flow Kind") == "Expense", prop("Flow Kind") == "Transfer"), -abs(prop("Amount")), 0))',
            "Recorded Income": 'if(prop("Flow Kind") == "Income", abs(prop("Amount")), 0)',
            "Recorded Expense": 'if(prop("Flow Kind") == "Expense", abs(prop("Amount")), 0)',
            "Transfer Check": 'if(prop("Flow Kind") == "Transfer", if(or(empty(prop("Account Link")), empty(prop("Transfer Destination"))), "Complete both accounts", "Check source and destination"), "")',
        },
        "Accounts": {
            "Recorded Balance": 'prop("Opening Balance") + prop("Account Entries").map(current.prop("Signed Movement")).sum() + prop("Incoming Transfers").filter(current.prop("Flow Kind") == "Transfer").map(abs(current.prop("Amount"))).sum()',
        },
        "Monthly Budgets": {
            "Linked Spending": 'prop("Budget Entries").map(current.prop("Recorded Expense")).sum()',
            "Live Budget Left": 'prop("Budget") - prop("Linked Spending")',
            "Budget Signal": 'if(prop("Budget") <= 0, "Set a budget", if(prop("Linked Spending") > prop("Budget"), "Over budget", if(prop("Linked Spending") >= prop("Budget") * 0.8, "Review spending", "Within plan")))',
            "Budget Progress": 'if(prop("Budget") <= 0, "Set budget", repeat("●", floor(min(1, max(0, prop("Linked Spending") / prop("Budget"))) * 10)) + repeat("○", 10 - floor(min(1, max(0, prop("Linked Spending") / prop("Budget"))) * 10)) + " " + format(round(prop("Linked Spending") / prop("Budget") * 100)) + "% used")',
        },
        "Savings Goals": {
            "Linked Contributions": 'prop("Contribution Entries").map(current.prop("Goal Contribution")).sum()',
            "Goal Progress": 'if(prop("Target Amount") <= 0, "Set target", repeat("●", floor(min(1, max(0, (prop("Saved Amount") + prop("Linked Contributions")) / prop("Target Amount"))) * 10)) + repeat("○", 10 - floor(min(1, max(0, (prop("Saved Amount") + prop("Linked Contributions")) / prop("Target Amount"))) * 10)) + " " + format(round((prop("Saved Amount") + prop("Linked Contributions")) / prop("Target Amount") * 100)) + "%")',
        },
    },
    "student": {
        "Assignments": {
            "Done Unit": 'if(or(prop("Status") == "Done", or(prop("Status") == "Completed", prop("Status") == "Submitted")), 1, 0)',
            "Remaining Hours": 'if(prop("Done Unit") == 1, 0, max(0, prop("Estimated Hours")))',
            "Graded Weight": 'if(and(prop("Graded"), prop("Points Possible") > 0), max(0, prop("Weight %")), 0)',
            "Weighted Points": 'if(and(prop("Graded"), prop("Points Possible") > 0), prop("Points Earned") / prop("Points Possible") * max(0, prop("Weight %")), 0)',
            "Deadline Signal": 'if(prop("Done Unit") == 1, "Complete", if(empty(prop("Due Date")), "Set deadline", if(prop("Due Date") < today(), "Overdue", if(dateBetween(prop("Due Date"), today(), "days") <= 3, "Due soon", "Planned"))))',
        },
        "Courses": {
            "Open Study Hours": 'prop("Assignment Entries").filter(and(current.prop("Done Unit") == 0, and(not empty(current.prop("Due Date")), current.prop("Due Date") <= dateAdd(today(), 7, "days")))).map(current.prop("Remaining Hours")).sum()',
            "Weekly Workload": 'if(prop("Weekly Study Capacity") <= 0, "Set weekly hours", if(prop("Open Study Hours") > prop("Weekly Study Capacity"), "Over capacity", "Room to study"))',
            "Current Graded Average": 'if(prop("Assignment Entries").map(current.prop("Graded Weight")).sum() <= 0, "Not graded yet", format(round(prop("Assignment Entries").map(current.prop("Weighted Points")).sum() / prop("Assignment Entries").map(current.prop("Graded Weight")).sum() * 1000) / 10) + "%")',
            "Course Completion": 'if(empty(prop("Assignment Entries")), "No assignments", format(round(prop("Assignment Entries").map(current.prop("Done Unit")).sum() / prop("Assignment Entries").length() * 100)) + "% complete")',
        },
    },
    "creator": {
        "Production Pipeline": {
            "Production Focus": 'if(not empty(prop("Blocker")), "Blocked: " + prop("Blocker"), if(not empty(prop("Next Action")), prop("Next Action"), "Set the next action"))',
            "Packaging Check": 'if(or(empty(prop("Title A")), or(empty(prop("Audience Promise")), empty(prop("Thumbnail Brief")))), "Complete title, promise and thumbnail brief", "Packaging brief ready")',
            "Release Check": 'if(not empty(prop("Blocker")), "Resolve blocker", if(prop("Packaging Check") != "Packaging brief ready", "Finish packaging", if(prop("Thumbnail Status") != "Ready", "Prepare thumbnail", "Ready for final review")))',
        },
        "Performance": {
            "Subscribers per 1k Views": 'if(prop("Views") <= 0, 0, prop("Subscribers Gained") / prop("Views") * 1000)',
            "Learning Status": 'if(empty(prop("Result Notes")), "Review pending", if(empty(prop("Next Experiment")), "Choose next experiment", "Learning captured"))',
        },
    },
    "habits": {
        "Habit Log": {
            "Full Credit": 'if(or(prop("Completion Mode") == "Full", and(empty(prop("Completion Mode")), prop("Completed"))), 1, 0)',
            "Minimum Credit": 'if(prop("Completion Mode") == "Minimum", 1, 0)',
            "Rhythm Label": 'if(not empty(prop("Completion Mode")), prop("Completion Mode"), if(prop("Completed"), "Full", "Not recorded"))',
        },
        "Habits": {
            "Full Days Last 7": 'prop("Habit Entries").filter(and(not empty(current.prop("Date")), and(current.prop("Date") >= dateSubtract(today(), 6, "days"), current.prop("Date") <= today()))).map(current.prop("Full Credit")).sum()',
            "Minimum Days Last 7": 'prop("Habit Entries").filter(and(not empty(current.prop("Date")), and(current.prop("Date") >= dateSubtract(today(), 6, "days"), current.prop("Date") <= today()))).map(current.prop("Minimum Credit")).sum()',
            "Seven Day Rhythm": 'if(prop("Goal Per Week") <= 0, "Set a weekly goal", repeat("●", floor(min(1, prop("Full Days Last 7") / prop("Goal Per Week")) * 10)) + repeat("○", 10 - floor(min(1, prop("Full Days Last 7") / prop("Goal Per Week")) * 10)) + " " + format(prop("Full Days Last 7")) + "/" + format(prop("Goal Per Week")) + " full")',
            "Restart Cue": 'if(prop("Full Days Last 7") + prop("Minimum Days Last 7") == 0, if(empty(prop("Restart Plan")), "Choose one tiny action", prop("Restart Plan")), "Keep your rhythm")',
        },
    },
    "freelancer": {
        "Tasks": {
            "Remaining Task": 'if(or(prop("Status") == "Done", prop("Status") == "Completed"), 0, 1)'
        },
        "Invoices": {
            "Recorded Receipts": 'if(prop("Payment Status") == "Paid", prop("Amount"), min(max(0, prop("Amount Received")), max(0, prop("Amount"))))',
            "Outstanding Balance": 'if(or(prop("Payment Status") == "Cancelled", prop("Payment Status") == "Void"), 0, max(0, prop("Amount") - prop("Recorded Receipts")))',
            "Receipt State": 'if(prop("Outstanding Balance") <= 0, "Settled or void", if(prop("Recorded Receipts") > 0, "Partial", "Outstanding"))',
            "Overdue Balance": 'if(and(prop("Outstanding Balance") > 0, and(not empty(prop("Due Date")), prop("Due Date") < today())), prop("Outstanding Balance"), 0)',
        },
        "Projects": {
            "Logged Hours": 'prop("Task Entries").map(current.prop("Hours Logged")).sum()',
            "Fee per Logged Hour": 'if(prop("Logged Hours") <= 0, 0, prop("Fee") / prop("Logged Hours"))',
            "Scope Signal": 'if(not empty(prop("Change Request")), "Review change request", if(prop("Included Revisions") <= 0, "Set revision allowance", if(prop("Revisions Used") > prop("Included Revisions"), "Outside revision allowance", "Within revision allowance")))',
            "Hours Signal": 'if(prop("Hours Budget") <= 0, "Set hours budget", if(prop("Logged Hours") > prop("Hours Budget"), "Over hours budget", "Within hours budget"))',
            "Delivery Progress": 'if(empty(prop("Task Entries")), "No linked tasks", format(round((1 - prop("Task Entries").map(current.prop("Remaining Task")).sum() / prop("Task Entries").length()) * 100)) + "% delivered")',
        },
        "Clients": {
            "Outstanding Invoices": 'prop("Invoice Entries").map(current.prop("Outstanding Balance")).sum()'
        },
    },
}


FORMULAS["finance"]["Transactions"]["In Current Month"] = (
    'if(empty(prop("Date")), false, formatDate(prop("Date"), "YYYY-MM") == formatDate(today(), "YYYY-MM"))'
)
FORMULAS["finance"]["Monthly Budgets"]["In Current Month"] = (
    'if(empty(prop("Month Start")), false, formatDate(prop("Month Start"), "YYYY-MM") == formatDate(today(), "YYYY-MM"))'
)
FORMULAS["habits"]["Habit Log"]["Is Today"] = (
    'if(empty(prop("Date")), false, formatDate(prop("Date"), "YYYY-MM-DD") == formatDate(today(), "YYYY-MM-DD"))'
)

# Native rollups keep relation aggregation explicit and compatible with Notion's schema API.
ROLLUPS = {
    "finance": {
        "Accounts": {
            "Ledger Total": ("Account Entries", "Signed Movement", "sum"),
            "Incoming Transfer Total": ("Incoming Transfers", "Incoming Transfer Amount", "sum"),
        },
        "Monthly Budgets": {"Linked Spending": ("Budget Entries", "Recorded Expense", "sum")},
        "Savings Goals": {
            "Linked Contributions": ("Contribution Entries", "Goal Contribution", "sum")
        },
    },
    "student": {
        "Courses": {
            "Open Study Hours": ("Assignment Entries", "Due Within Week Hours", "sum"),
            "Graded Weight Total": ("Assignment Entries", "Graded Weight", "sum"),
            "Weighted Points Total": ("Assignment Entries", "Weighted Points", "sum"),
            "Completed Assignment Count": ("Assignment Entries", "Done Unit", "sum"),
            "Assignment Count": ("Assignment Entries", "Task", "count"),
        },
    },
    "habits": {
        "Habits": {
            "Full Days Last 7": ("Habit Entries", "Full Last Seven", "sum"),
            "Minimum Days Last 7": ("Habit Entries", "Minimum Last Seven", "sum"),
        },
    },
    "freelancer": {
        "Projects": {
            "Logged Hours": ("Task Entries", "Hours Logged", "sum"),
            "Open Task Count": ("Task Entries", "Remaining Task", "sum"),
            "Task Count": ("Task Entries", "Task", "count"),
        },
        "Clients": {"Outstanding Invoices": ("Invoice Entries", "Outstanding Balance", "sum")},
    },
}
FORMULAS["finance"]["Transactions"]["Incoming Transfer Amount"] = (
    'if(prop("Flow Kind") == "Transfer", abs(prop("Amount")), 0)'
)
FORMULAS["finance"]["Accounts"]["Recorded Balance"] = (
    'prop("Opening Balance") + prop("Ledger Total") + prop("Incoming Transfer Total")'
)
FORMULAS["student"]["Assignments"]["Due Within Week Hours"] = (
    'if(and(prop("Done Unit") == 0, and(not empty(prop("Due Date")), prop("Due Date") <= dateAdd(today(), 7, "days"))), prop("Remaining Hours"), 0)'
)
FORMULAS["student"]["Courses"]["Current Graded Average"] = (
    'if(prop("Graded Weight Total") <= 0, "Not graded yet", format(round(prop("Weighted Points Total") / prop("Graded Weight Total") * 1000) / 10) + "%")'
)
FORMULAS["student"]["Courses"]["Course Completion"] = (
    'if(prop("Assignment Count") <= 0, "No assignments", format(round(prop("Completed Assignment Count") / prop("Assignment Count") * 100)) + "% complete")'
)
FORMULAS["habits"]["Habit Log"]["Full Last Seven"] = (
    'if(and(not empty(prop("Date")), and(prop("Date") >= dateSubtract(today(), 6, "days"), prop("Date") <= today())), prop("Full Credit"), 0)'
)
FORMULAS["habits"]["Habit Log"]["Minimum Last Seven"] = (
    'if(and(not empty(prop("Date")), and(prop("Date") >= dateSubtract(today(), 6, "days"), prop("Date") <= today())), prop("Minimum Credit"), 0)'
)
FORMULAS["freelancer"]["Projects"]["Delivery Progress"] = (
    'if(prop("Task Count") <= 0, "No linked tasks", format(round((1 - prop("Open Task Count") / prop("Task Count")) * 100)) + "% delivered")'
)
for _key, _tables in ROLLUPS.items():
    for _table, _fields in _tables.items():
        for _name in _fields:
            FORMULAS.get(_key, {}).get(_table, {}).pop(_name, None)

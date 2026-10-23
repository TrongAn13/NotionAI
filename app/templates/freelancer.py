from app.templates.base import Formula, Template, text

SPEC = Template(
    title="Freelancer Business OS",
    icon="💼",
    tagline="Keep client work, delivery and payments moving together.",
    features=[
        "Maintain client details and a visible lead pipeline.",
        "Track projects, next actions, deadlines and invoices.",
        "Flag overdue unpaid invoices and review revenue from recorded payments.",
    ],
    workflow=[
        "Capture a lead and schedule the next follow-up; contact people manually.",
        "Create a project and tasks when work is agreed, then track delivery deadlines.",
        "Record an invoice and update Payment Status only when payment is confirmed.",
        "Review overdue invoices and your payment totals every week.",
    ],
    manual=[
        "Create a Leads board grouped by Stage and sorted by Next Follow Up.",
        "Create a project task view filtered to unfinished work and sorted by Due Date.",
        "Create an Invoices view filtered to NTB Overdue = checked.",
        "Group Invoices by month and sum NTB Paid Revenue; choose your currency.",
        "NTB Paid Revenue counts only Payment Status = Paid. Partial payments need a separate payment ledger.",
        "Clients and projects are text fields in the starter; optional relations must be configured manually.",
        "No invoices are sent and no clients are contacted automatically.",
    ],
    properties={"Projects": {"Next Action": text()}, "Clients": {"Contact Notes": text()}},
    formulas={
        "Invoices": [
            Formula(
                "NTB Overdue",
                'if(empty(prop("Due Date")), false, and(prop("Due Date") < today(), prop("Payment Status") != "Paid"))',
                {"Due Date": "date", "Payment Status": "select"},
            ),
            Formula(
                "NTB Paid Revenue",
                'if(prop("Payment Status") == "Paid", prop("Amount"), 0)',
                {"Payment Status": "select", "Amount": "number"},
            ),
        ]
    },
)

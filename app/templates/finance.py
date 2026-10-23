from app.templates.base import Formula, Template, number

SPEC = Template(
    title="Personal Finance Tracker",
    icon="💰",
    tagline="Know your cash flow. Give every goal a clear next step.",
    features=[
        "Capture income and expenses by account and category.",
        "Plan monthly budgets and track savings goals.",
        "Review cash flow and savings progress without inventing balances.",
    ],
    workflow=[
        "Record a real transaction with its date, account, type and amount.",
        "Use positive amounts; choose Income or Expense to set the cash-flow direction.",
        "Review monthly totals, compare spending with your budget and update actual savings.",
    ],
    manual=[
        "Create a monthly Transactions view grouped by month; sum NTB Cash Flow.",
        "Filter expenses by category and compare their sums with Monthly Budgets.",
        "For live account balances, connect Transactions to Accounts with relations and rollups.",
        "NTB Budget Remaining uses Actual Spending entered manually; it is not a live rollup.",
        "Choose your currency and format NTB Savings Progress as a percentage.",
    ],
    properties={"Monthly Budgets": {"Actual Spending": number()}},
    formulas={
        "Transactions": [
            Formula(
                "NTB Cash Flow",
                'if(prop("Type") == "Income", abs(prop("Amount")), if(prop("Type") == "Expense", -abs(prop("Amount")), 0))',
                {"Type": "select", "Amount": "number"},
            )
        ],
        "Savings Goals": [
            Formula(
                "NTB Savings Progress",
                'if(prop("Target Amount") <= 0, 0, min(1, max(0, prop("Saved Amount") / prop("Target Amount"))))',
                {"Target Amount": "number", "Saved Amount": "number"},
                True,
            )
        ],
        "Monthly Budgets": [
            Formula(
                "NTB Budget Remaining",
                'prop("Budget") - prop("Actual Spending")',
                {"Budget": "number", "Actual Spending": "number"},
            )
        ],
    },
)

from app.templates.base import Formula, Template, number, text

SPEC = Template(
    title="Habit & Productivity Tracker",
    icon="🌱",
    tagline="Build consistency with small actions and useful weekly reviews.",
    features=[
        "Log daily habit completion and keep weekly goals visible.",
        "Review completion rates using actual habit logs.",
        "Reflect on the week and record a monthly lesson.",
    ],
    workflow=[
        "Choose a small habit and a realistic weekly frequency.",
        "Add a Habit Log entry each day and mark Completed only when done.",
        "Review the week, adjust your goals and capture one lesson for next month.",
    ],
    manual=[
        "Create a Habit Log view filtered to this week; average NTB Completion Score for logged-entry completion rate.",
        "Missing daily entries are not counted; log skipped days as incomplete for a meaningful rate.",
        "Create a Goals view filtered to this week's targets and update Actual and Target manually.",
        "Use Monthly Reflection in Weekly Review on the final review of each month.",
        "Format NTB Goal Progress and average NTB Completion Score as percentages.",
    ],
    properties={
        "Goals": {"Actual": number(), "Target": number()},
        "Weekly Review": {"Monthly Reflection": text(), "Next Action": text()},
    },
    formulas={
        "Habit Log": [
            Formula(
                "NTB Completion Score", 'if(prop("Completed"), 1, 0)', {"Completed": "checkbox"}
            )
        ],
        "Goals": [
            Formula(
                "NTB Goal Progress",
                'if(prop("Target") <= 0, 0, min(1, max(0, prop("Actual") / prop("Target"))))',
                {"Target": "number", "Actual": "number"},
                True,
            )
        ],
    },
)

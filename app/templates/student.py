from app.templates.base import Formula, Template, number, text

SPEC = Template(
    title="Student Planner",
    icon="🎓",
    tagline="See what is due. Make room for focused learning.",
    features=[
        "Keep courses, assignments, exams and study sessions in one place.",
        "Spot upcoming deadlines and plan work by priority.",
        "Track course progress with completed and total units you enter.",
    ],
    workflow=[
        "Add your courses, then capture real assignment and exam dates.",
        "Estimate assignment effort and reserve study sessions for the coming week.",
        "Complete work, update course units and review the next seven days.",
    ],
    manual=[
        "Create a weekly Study Sessions calendar using Date.",
        "Create an Assignments view sorted by Due Date and filtered to unfinished work.",
        "Create an Exams calendar and optionally relate coursework to Courses.",
        "Completed Units and Total Units are manual counts; format progress as a percentage.",
        "Demo workflow: create a test assignment yourself, review it, then remove it if unwanted.",
    ],
    properties={
        "Courses": {"Completed Units": number(), "Total Units": number()},
        "Study Sessions": {"Study Goal": text()},
    },
    formulas={
        "Assignments": [
            Formula(
                "NTB Days Until Deadline",
                'if(empty(prop("Due Date")), "", format(dateBetween(prop("Due Date"), now(), "days")))',
                {"Due Date": "date"},
            )
        ],
        "Exams": [
            Formula(
                "NTB Days Until Exam",
                'if(empty(prop("Date")), "", format(dateBetween(prop("Date"), now(), "days")))',
                {"Date": "date"},
            )
        ],
        "Courses": [
            Formula(
                "NTB Course Progress",
                'if(prop("Total Units") <= 0, 0, min(1, max(0, prop("Completed Units") / prop("Total Units"))))',
                {"Total Units": "number", "Completed Units": "number"},
                True,
            )
        ],
    },
)

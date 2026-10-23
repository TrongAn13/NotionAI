"""Focused workspaces inside existing course, video, habit and client records."""

from app.premium.views import view
from app.templates.dashboard import block, rich

PLAYBOOKS = {
    "finance": {
        "Monthly Budgets": [
            (
                "Monthly money review",
                [
                    "What changed between your plan and actual spending?",
                    "Which expense was worth keeping?",
                    "Choose one adjustment for next month.",
                ],
            )
        ],
    },
    "student": {
        "Courses": [
            (
                "Course studio",
                [
                    "Keep your syllabus and assessment rules here.",
                    "Capture key questions and connect your study sessions to this course.",
                ],
            ),
            ("Notes & resources", ["Lecture notes", "Reading questions", "Reference links"]),
        ],
        "Exams": [
            (
                "Exam sprint",
                [
                    "List the topics and mark the weakest ones.",
                    "Reserve study sessions before the real exam date.",
                    "Test recall with practice questions, then update Readiness.",
                ],
            )
        ],
    },
    "creator": {
        "Production Pipeline": [
            (
                "Video production brief",
                [
                    "Audience: who needs this video and what problem does it solve?",
                    "Promise: what should the viewer understand or do afterward?",
                    "Proof: which examples, sources or demonstrations support the promise?",
                ],
            ),
            (
                "Packaging lab",
                [
                    "Write two accurate title approaches in Title A and Title B.",
                    "Define one thumbnail idea in Thumbnail Brief and attach candidates to Thumbnail A/B.",
                    "Choose the hook and the first visual before drafting the full script.",
                ],
            ),
            (
                "Script & storyboard",
                [
                    "Hook → context → main beats → proof → next step.",
                    "For each beat record the spoken point, visual, source and asset needed.",
                ],
            ),
            (
                "Release review",
                [
                    "Check accuracy, rights, sound, thumbnail legibility and title promise.",
                    "Clear the Blocker field and record the next action.",
                    "Publish manually, then connect a Performance entry with its measurement window.",
                ],
            ),
        ],
        "Performance": [
            (
                "Learning loop",
                [
                    "Record what you expected before interpreting the numbers.",
                    "Compare the same channel and the same measurement window.",
                    "Write one finding in Result Notes and one change in Next Experiment.",
                ],
            )
        ],
        "Channels": [
            (
                "Channel strategy",
                [
                    "Audience and recurring problem",
                    "Content pillars and publishing cadence",
                    "What to repeat, test and stop",
                ],
            )
        ],
    },
    "habits": {
        "Habits": [
            (
                "Your minimum-day plan",
                [
                    "Define the full action in Full Version.",
                    "Define a genuinely small alternative in Minimum Version.",
                    "Choose a concrete cue and write the next restart action.",
                    "Full and Minimum are recorded separately. Rest is neither a win nor a failure.",
                ],
            )
        ],
    },
    "freelancer": {
        "Clients": [
            (
                "Client room",
                [
                    "Keep the brief, contact preferences and decision history together.",
                    "Use the linked project and invoice views below for internal tracking.",
                    "This page is private. Prepare and permission a separate delivery surface before client sharing.",
                ],
            )
        ],
        "Projects": [
            (
                "Kickoff & scope",
                [
                    "Outcome and agreed deliverables",
                    "What is included and excluded",
                    "Dates, dependencies and who approves the work",
                ],
            ),
            (
                "Scope guard",
                [
                    "Enter the included revision allowance and actual rounds used.",
                    "Record new requests in Change Request before agreeing to extra work.",
                    "Record actual task hours; Fee per Logged Hour is revenue per logged hour, not profit.",
                ],
            ),
            (
                "Handoff",
                [
                    "Deliver final files and documentation.",
                    "Confirm acceptance and record any remaining tasks.",
                    "Review invoice balances and request feedback manually.",
                ],
            ),
        ],
    },
}

HUBS = {
    ("student", "Courses"): [
        view(
            "Assignments",
            "Course assignments",
            columns=["Task", "Due Date", "Priority", "Status", "Deadline Signal"],
        ),
        view(
            "Study Sessions",
            "Course study sessions",
            columns=["Session", "Date", "Topic", "Review On", "Confidence"],
        ),
    ],
    ("creator", "Channels"): [
        view(
            "Production Pipeline",
            "Channel production",
            "board",
            ["Target Date", "Production Focus"],
            group="Production Stage",
        ),
        view(
            "Publishing Calendar",
            "Channel releases",
            "calendar",
            ["Status", "Production Link"],
            date="Publish Date",
        ),
    ],
    ("creator", "Production Pipeline"): [
        view(
            "Performance",
            "Video learning log",
            columns=[
                "Snapshot On",
                "Window",
                "Views",
                "NTB Engagement Rate",
                "Result Notes",
                "Next Experiment",
            ],
        )
    ],
    ("habits", "Habits"): [
        view(
            "Habit Log", "Habit rhythm history", "calendar", ["Rhythm Label", "Notes"], date="Date"
        )
    ],
    ("freelancer", "Clients"): [
        view(
            "Projects",
            "Client projects",
            "gallery",
            ["Due Date", "Delivery Progress", "Scope Signal"],
        ),
        view(
            "Invoices",
            "Client invoices",
            columns=["Invoice", "Amount", "Outstanding Balance", "Receipt State", "Due Date"],
        ),
    ],
    ("freelancer", "Projects"): [
        view(
            "Tasks",
            "Project deliveries",
            columns=["Task", "Due Date", "Priority", "Status", "Hours Logged"],
        ),
        view(
            "Invoices",
            "Project invoices",
            columns=["Invoice", "Amount", "Outstanding Balance", "Due Date"],
        ),
    ],
}


def hub_relation(key, table):
    if key == "student":
        return "Course Link"
    if key == "creator":
        return "Channel Link" if table == "Channels" else "Production Link"
    if key == "habits":
        return "Habit Link"
    return "Client Link" if table == "Clients" else "Project Link"


def record_blocks(key, table, record_id):
    marker = f"https://www.notion.so/{record_id.replace('-', '')}#workspace-v2"
    intro = block("paragraph")
    intro["paragraph"]["rich_text"] = [rich("Your working space", marker, color="gray")]
    children = [intro]
    for heading, prompts in PLAYBOOKS[key][table]:
        children += [block("heading_2", heading)]
        children += [block("bulleted_list_item", text) for text in prompts]
    children += [block("divider")]
    return marker, children

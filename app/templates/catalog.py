from app.templates import creator, finance, freelancer, habits, student

SPECS = {
    "finance": finance.SPEC,
    "student": student.SPEC,
    "creator": creator.SPEC,
    "habits": habits.SPEC,
    "freelancer": freelancer.SPEC,
}
VERSION = "1.0.0"

EXPECTED_DATABASES = {
    "finance": ["Accounts", "Monthly Budgets", "Savings Goals", "Transactions"],
    "student": ["Assignments", "Courses", "Exams", "Study Sessions"],
    "creator": ["Channels", "Ideas", "Performance", "Production Pipeline", "Publishing Calendar"],
    "habits": ["Goals", "Habit Log", "Habits", "Weekly Review"],
    "freelancer": ["Clients", "Invoices", "Leads", "Projects", "Tasks"],
}

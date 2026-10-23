# Premium template redesign — V2 product brief

Research date: 2026-10-23. Status: proposal only; no Notion mutations performed in this research turn.
Public product listings, feature descriptions and previews were reviewed; purchased internals were not audited.
Observed listing prices are reference points, not proof of demand or sales performance.

## Market references

| Area | Reference | Observed offer | What to learn |
| --- | --- | --- | --- |
| Finance | Easlo Finance Tracker | $39 | Connected accounts, monthly reporting, transfers, budgets and goals. |
| Student | The Organized Club Student Planner | $8.44 | A visual academic hub, planner, coursework and reusable covers. |
| Student | Gridfiti Student OS | Feature reference; price not used | Course hubs, weighted grades, related notes and study workflows. |
| Creator | Thomas Frank Creator's Companion | Base displayed at $99 promotional / $149 list | End-to-end production views plus onboarding and support. |
| Habits | Easlo Habit Journal | $9 | Habits connected to daily journaling and mood. |
| Freelancer | Easlo Freelance OS | $79 individual | CRM, deal pipeline, tasks, meetings, invoices and resources linked together. |

Sources:
- https://www.easlo.co/templates/finance-tracker
- https://theorganizedclub.gumroad.com/l/notion-template-student-planner
- https://gridfiti.com/notion-templates-for-students/
- https://thomasjfrank.com/creators-companion/
- https://www.easlo.co/templates/habit-journal
- https://easlo.gumroad.com/l/freelanceos
- https://www.easlo.co/templates/freelancer-operating-system

## Product direction

The current upgrade added useful schema and documentation, but retained a text-heavy page and
appended the guide at the bottom. V2 must redesign the working surface, connect existing data,
and deliver a specific repeatable workflow for each buyer.

One shared brand family; five distinct product identities. Shared components: navigation,
three-step onboarding, restrained icons, consistent covers, obvious primary action, empty states,
mobile ordering, help in a secondary location. Each product gets original cover artwork and its
own useful visual motif. Avoid stock motivational quotes and decorative widgets that add friction.

Core views, relations and buttons must be finished in the sellable product. A buyer should not
receive a technical setup checklist for the essential workflow. Any API gap must be resolved by
the seller in Notion UI before release; verify actual API support at implementation time.

All names below are working titles, pending brand checks. All mockup values are fictional and
must never be imported into the user's working databases. No existing resources are to be
recreated. Existing user values remain intact; new relations supplement old text/select fields.

## Personal Finance Tracker → Clarity Money

Audience: salaried users managing a monthly budget and building a savings buffer.
Promise: see where this month's money went and the next sensible action to review.
Visual identity: sage, ink and paper; original editorial cover; quiet account cards and legible
budget bars. No trading-terminal aesthetic or invented investment returns.

Dashboard hierarchy:
1. Compact cover, month context and entry points for Expense, Income and Review.
2. Actual monthly income, spending and budget remaining, clearly labeled with their period.
3. Budget by category with spent/budget bars and explicit over-budget states.
4. Account balance gallery beside savings goals.
5. Recent transactions and monthly review prompts; full guide in a secondary location.

Signature features:
- Payday planning: allocate real monthly income to essentials, flexible spending and savings.
- Budget signals: show category variance and remaining allocation from linked transactions.
- Monthly review: compare plan with actuals and capture one change for next month.

Data upgrade using the four existing databases:
- Transactions: preserve Account select; add an Account relation with unambiguous migration only.
- Monthly Budgets: preserve Month title; add explicit period/category and related transactions.
- Accounts: opening balance plus related signed movements; transfers need explicit source/destination
  representation and must never count as income/expense. Do not infer ambiguous transfer mappings.
- Savings Goals: retain actual entered savings; any automatic contribution rollup needs a real link.
- No live bank connection, automatic exchange rates or tax calculations in the core product.
- Subscriptions are an optional later module, not another empty table added to inflate features.

Acceptance: adding one expense changes its linked category total, monthly total and account balance;
a transfer changes account balances but not income/expense; zero targets and empty dates are safe;
new months do not require rewriting formulas; ambiguous old labels are reported for review.
Suggested price test after completion: $19–29. Hypothesis only.

## Student Planner → Semester Studio

Audience: university students juggling multiple courses and near-term deadlines.
Promise: know what to study next and whether the coming week is overloaded.
Visual identity: lilac, navy and warm paper; original abstract notebook cover; course galleries
with consistent subject covers. Academic information remains readable without decorative embeds.

Dashboard hierarchy:
1. Current semester, today's timetable and the next meaningful action.
2. Due soon list and this week's assignment workload.
3. Course cards linking to each course's notes, assignments, exams and resources.
4. Exam preparation area with revision topics and the next scheduled session.
5. Semester review and archive navigation.

Signature features:
- Workload check: compare manually declared available study hours with estimated unfinished effort.
- Exam sprint: create a revision plan backwards from the exam, with topic confidence and practice checks.
- Weighted grade view: distinguish earned contribution, current graded average and still-ungraded work.

Data upgrade:
- Preserve Course text fields; add relations to Courses in Assignments, Exams and Study Sessions.
- Derive progress from related completed work rather than only manual Completed Units/Total Units.
- Assignment grade inputs: earned points, possible points, assessment weight and graded state.
- No universal GPA claim: grading scales and course policy must be configurable.
- Reuse course page bodies for structured notes; a separate Notes or Revision Topics database is
  optional and requires deliberate creation beyond the initial no-new-database constraint.

Acceptance: a new related assignment appears in its course and weekly view; an ungraded assignment
does not reduce the current graded average; invalid/missing weights are visible; the mobile first
screen shows deadlines and next study action before references.
Suggested price test: $19–29 after a connected core is complete.

## Content Creator OS → Channel Studio

Audience: solo YouTube creators or small production teams with one to five channels.
Promise: every video has a clear next production action and a useful learning record.
Visual identity: ink, clay and off-white; original film/production covers; thumbnail-based cards,
compact status labels and a deliberate editorial hierarchy.

Dashboard hierarchy:
1. Current channel context, capture-idea action and next releases.
2. Production board with thumbnails, stage, owner, deadline and blocker.
3. Publishing calendar connected to the same content items.
4. Packaging area for title hypotheses and thumbnail briefs.
5. Performance and a compact post-publication learning log.

Signature features:
- Packaging before production: audience problem, promise, hook, title and thumbnail rationale.
- Blocker view: show what prevents the next release, rather than only colorful status columns.
- Repurpose map: link a long-form video to derivative Shorts or posts.
- Learning loop: save the original hypothesis, 7/28-day metrics and the next experiment.

Data upgrade using the five existing databases:
- Channels becomes the relation hub for Ideas, Production Pipeline and Publishing Calendar.
- Keep existing records separate; link an idea, its production item, scheduled release and
  performance snapshots through explicit relations. Do not silently create a replacement master DB.
- Preserve Performance's original numbers; add snapshot date/window for meaningful comparison.
- CTR and average view duration are user-entered/imported only when available; do not infer them
  from likes or views. Compare content within the same channel and reporting window.
- AI prompt library lives in reusable video briefs, with inputs and review criteria.
- No automatic publishing, analytics import, sponsor outreach or A/B testing service is implied.

Acceptance: opening a production card reveals a complete reusable brief; schedule and performance
can be traced to the same video; an edited date updates the related release view; board cards make
blockers obvious; a first-time user can capture an idea without configuring schemas.
Suggested price test: $39–59 for the connected solo-creator edition.

## Habit & Productivity → Momentum

Audience: people who abandon trackers when a streak breaks or their energy varies.
Promise: make a small action easy to resume and see consistency honestly.
Visual identity: muted amber, warm paper and original rhythm/stepping-stone artwork.
Avoid a copied RPG, garden metaphor or dozens of decorative rewards.

Dashboard hierarchy:
1. Today view with a small set of scheduled habits.
2. Each habit displays its Full and Minimum version and a simple completion choice.
3. Weekly rhythm distinguishing Full, Minimum, Skipped and planned Rest.
4. Weekly reset connecting an observation to a practical change.
5. Goal progress from actual related activity when meaningful.

Signature features:
- Minimum day: a deliberate low-effort action without pretending it equals full completion.
- Restart plan: a saved tiny action and cue for the next scheduled opportunity.
- Honest consistency: scheduled opportunities are the denominator; days with no logs are not
  silently ignored, and Rest is not counted as either a success or a failure.

Data upgrade using Habits, Habit Log, Goals and Weekly Review:
- Preserve Habit text and Completed checkbox; add a Habit relation and an explicit completion mode.
- Add the planned schedule, Full/Minimum definitions and cue on the habit record.
- Track expected opportunities separately from observed logs to avoid inflated completion rates.
- No current streak claim based on only three recent entries; reporting windows are explicit.
- Monthly reflection can remain in Weekly Review records; no new reflection DB is required.

Acceptance: Rest does not break an eligible-day sequence; a planned but unlogged day is visible;
Minimum and Full counts remain distinct; a low-energy day takes fewer interactions; users can
understand the calculation without reading a technical guide.
Suggested price test: $12–19 for a focused product rather than a bloated life OS.

## Freelancer Business OS → Client Desk

Audience: independent designers, video editors, writers and similar project-based service providers.
Promise: know what to deliver next, what is unpaid and where scope is expanding.
Visual identity: slate blue and paper with original studio/deliverable covers; client and project
cards, compact financial summaries and timeline-oriented views.

Dashboard hierarchy:
1. Today: due tasks, follow-ups and items awaiting client response.
2. Lead pipeline and active project board/timeline.
3. Outstanding balances, upcoming payments and overdue invoices.
4. Planned capacity and project delivery health.
5. Reusable brief, kickoff and handoff resources.

Signature features:
- Scope guard: agreed deliverables and revision allowance versus actual requests.
- Project economics: distinguish fee, cash received, estimated/logged hours, direct expenses and
  effective hourly revenue. Do not label revenue/hour as profit or estimated margin as actual margin.
- Client space: a separately permissioned, curated delivery surface without internal margins/notes.

Data upgrade using the five existing databases:
- Add relations Clients ↔ Projects ↔ Tasks/Invoices; retain original text fields.
- Reuse Leads, linking an accepted lead to its client/project rather than recreating it.
- Partial payments need explicit paid amount and remaining balance; a proper payment ledger is
  an optional later module. Do not double count the invoice amount as cash received.
- A separate Time Entries DB is optional; the first version can use recorded hours on Tasks with
  clear limits. Do not market a timer until one is implemented.
- Client portal filtering is not access control. Client-facing pages require deliberate permission
  tests with a guest account before any sharing; this proposal does not authorize sharing.

Acceptance: a task is discoverable from its client and project; partial payment reduces only the
remaining balance; extra revision requests are visible; private notes cannot be read from a client
surface; overdue views exclude settled balances; no invoice or message is sent automatically.
Suggested price test: $39–59 for a polished individual edition.

## Build order and release gates

Recommended sequence: Finance → Student → Creator → Momentum → Freelancer. Finance is a useful
first proof of the new standard: period filters, relations, live rollups, visuals and a clear
monthly workflow. Do not apply a generic text dashboard to all five again.

Per product:
1. Complete an inspectable dashboard design and user flow.
2. Plan additive schema/relationship changes against discovered resources.
3. Back up; preserve original IDs and user values; migrate only unambiguous links.
4. Build all essential native views, relations, page templates and working buttons before release.
5. Validate representative and empty inputs, date boundaries and duplicates after duplication.
6. Test the account/plan tier promised to customers and record actual dependencies.
7. Review desktop and mobile, create original covers and consistent screenshots, and record a short tour.
8. Prepare a clean sales edition only with explicit authorization. Never empty the working templates
   or add fictional financial transactions to them. A separate clean sales edition would require
   explicit authorization to create additional resources under the project's original constraint.

Core commercial package: finished template, short onboarding, realistic clearly-labeled examples
in a separate demo context, concise documentation, customization guide, support contact, license
terms and a version/upgrade policy. Automatic updates to duplicated buyer copies are not promised.

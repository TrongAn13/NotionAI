# Client Desk Design / Web Studio

Client Experience Studio adds independent client portals, content readiness, versioned reviews, decision logs and a fictional worked project. A native portal duplicate was verified inside the workspace and retained as Your first client portal. See [the client experience report](reports/client-experience-summary.md). Guest access, mobile and cross-workspace buyer duplication still need verification.

The working template now includes native project/change-request database templates, structured Scope Guard, project intake, approval gates and a reusable brief-to-handoff kit. See [the implementation and verification report](reports/client-desk-studio-summary.md) and [buyer guide](product/client-desk/BUYER-GUIDE.md). Seller identity and publishing remain deferred. Dry-run: `.venv\Scripts\python.exe -m app.premium.studio`.

# Notion Template Builder

Upgrade the five existing templates under My Template Store, preserving existing pages,
databases, records, properties and unrelated page blocks. The original creation script
and ZIP are retained for reference. Do not rerun `build_notion.py` to upgrade: it creates
duplicates.

## Windows PowerShell setup

Use Python 3.12 or later. Open PowerShell in this folder:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m app.main discover
```

Configure `NOTION_API_TOKEN` and `NOTION_PARENT_PAGE_ID` in `.env`, not `.env.example`.
The example contains the parent ID but no secret. Existing environment variables take
precedence. The application reads `.env` from the current directory. Tokens are never
printed or logged. Local `.env`, state, inventories and backups are Git-ignored.
Connect AnConnect to the parent page and grant read, insert and update content capability
for upgrades. Read-only discovery needs only read content. Keep the token private.
Activation is optional; explicit Python paths avoid PowerShell execution-policy issues.

## Commands

```powershell
.\.venv\Scripts\python.exe -m app.main discover
.\.venv\Scripts\python.exe -m app.main validate
.\.venv\Scripts\python.exe -m app.main plan
.\.venv\Scripts\python.exe -m app.main backup
.\.venv\Scripts\python.exe -m app.main upgrade --template all
.\.venv\Scripts\python.exe -m app.main upgrade --template creator --apply
.\.venv\Scripts\python.exe -m app.main status
```

`upgrade` defaults to dry-run. `--apply` displays the plan, asks for confirmation, saves
a JSON snapshot, then applies it. `--yes` provides explicit noninteractive confirmation
for an already authorized run. Choices: all, finance, student, creator, habits, freelancer.
`plan`, `validate`, `discover` and `status` never modify Notion. They may save local reports.
`status` reads local state only; use `plan` for live verification.

Exit codes: 0 success, 1 configuration/connection/execution failure, 2 incomplete inventory,
conflicts or verification requiring review. Configuration errors omit sensitive values.

## Implemented upgrade v1.0.0

- Finance: signed cash flow, savings progress, manually entered actual spending and budget remaining.
- Student: deadline and exam countdowns, study goal and course progress from manual unit counts.
- Creator: production pipeline stages, thumbnail status, draft fields, engagement rate and five AI prompts.
- Habits: daily completion score, manually entered goal progress and monthly reflection fields.
- Freelancer: contact notes, project next action, overdue detection and paid invoice revenue.
- All five: a managed guide with welcome, quick start, feature overview, database navigation,
  sample workflow, customization help, FAQ, setup checklist and version information.

The guide is one visible callout section appended to each existing page. Original page
content is preserved; move the guide higher manually if preferred. Existing database views
are unchanged. Relations, rollups, filtered views, native charts, scheduled notifications,
YouTube analytics import and publishing are not configured. Manual setup instructions
are provided without claiming these API capabilities are universally unavailable.

No sample records are inserted. Existing starter records remain available for learning.
New numeric inputs are empty until entered; percentages default to zero for zero targets.
Format ratios as percentages in Notion. Cash flow requires Type = Income or Expense and
positive amounts; paid revenue requires Payment Status = Paid. Partial payments need a
separate payment ledger. Overdue flags every past-due invoice whose status is not Paid.

## Safety and recovery

1. Discover all resources anew. Ambiguous titles, missing databases/data sources and
   incompatible formula inputs stop apply. The original habit title without `&` is accepted.
2. Add missing fields only. Never convert types, delete fields, change existing options,
   overwrite formulas or invent records. Fresh schema hashes prevent applying a stale plan.
3. Complete an accessible-resource snapshot before the first write. A backup failure stops apply.
4. Journal operations locally. A per-project lock prevents concurrent applies in this folder.
5. Store a unique marker, resource ID, version and content hash for each managed guide.
   Reruns verify the marker, ID and content. User-edited sections and lost manifests are conflicts.
6. Append requests are not retried after ambiguous transport/server failures. If the append
   succeeded but its response was lost, the pending manifest and exact content hash allow
   reconciliation without creating another guide. If no matching block is visible, stop and
   investigate rather than re-append blindly. Schema retries are reconciled by fresh discovery.
7. Re-inventory after apply and verify a repeat plan requires zero further operations.

Do not delete `state/manifest.json`. Do not run multiple checkouts against these pages
simultaneously. If interrupted, confirm no upgrade process is running before removing a
stale `state/upgrade.lock`, then run `plan`. Preserve manifest, backup and reports during
recovery. The current version detects content/version changes and requests manual review;
it does not automatically replace an older managed guide or overwrite edited content.

HTTP requests are sequential and paced. Read requests and rejected 429 responses use bounded
retries with backoff/jitter or Retry-After. Server errors on writes are left for reconciliation.
API error bodies and authorization headers are never included in reports. Snapshots contain
private workspace content: keep them local. JSON snapshots are not native Notion backups;
there is no automatic rollback. Files are not downloaded, temporary file URLs may expire,
comments are not exported, and page property values may be truncated by API response limits.

## Reports and local state

- `reports/inventory.json`, `reports/inventory.md`: discovery metadata, blocks and schemas.
- `reports/upgrade-plan.json`, `reports/upgrade-plan.md`: proposed additive operations.
- `reports/commercial-readiness-plan.md`: projected scope for the current plan.
- `reports/commercial-readiness.md`: last applied upgrade scope, manual tasks and publishing checklist.
- `reports/data-preservation-audit.json`: comparison of record values and original blocks against the backup.
- `reports/last-upgrade.json`, `reports/verification.json`: completed operations and fresh verification.
- `backups/snapshot-*.json` and accompanying `.plan.json`: snapshot before mutation and applied plan.
- `state/discovery.json`, `state/manifest.json`: observed resource IDs and durable ownership journal.

Discovery walks nested columns/toggles but does not follow nested child pages or linked
views when matching template databases. Backup recursively visits accessible child pages,
databases, queried records and nested block children within the selected templates.
Missing permissions cannot always be distinguished from missing resources.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
```

Unit tests use mocked HTTP or an in-memory workspace, never production credentials. They
cover discovery, pagination, conflicts, retries, data preservation, backup requirements,
schema races, formula compatibility, idempotency and recovery from a lost append response.
Formula syntax and property compatibility are checked against documented patterns and live
schema acceptance; local tests do not emulate the full Notion formula evaluator.

## Official API references (checked 2026-10-23)

Pinned API version: `2026-03-11`. Databases contain data sources; schema changes use the
data-source endpoint. Read-only record queries use POST as required by Notion.

- https://developers.notion.com/reference/versioning
- https://developers.notion.com/reference/retrieve-a-data-source
- https://developers.notion.com/reference/update-data-source-properties
- https://developers.notion.com/reference/query-a-data-source
- https://developers.notion.com/reference/block
- https://developers.notion.com/reference/request-limits

Nothing is publicly shared, published, sent to customers or enabled for duplication.


## Premium edition v2

The premium redesign keeps the original five pages, 22 data sources and all original
record values. New linked database containers are views of the same data; no standalone
replacement databases or sample records are created.

```powershell
.\.venv\Scripts\python.exe -m app.premium.backup
.\.venv\Scripts\python.exe -m app.main premium
.\.venv\Scripts\python.exe -m app.main premium --apply
```

The first command displays the proposed scope. Apply requires a completed premium backup
referenced by `state/premium-v2-backup.json`. The backup includes existing views, metadata,
blocks, schemas and all accessible queried records. The original backup pointer is retained
for journal recovery. Keep `state/premium-v2.json` alongside the v1 manifest. Reruns validate
managed views and reuse journaled operations instead of creating duplicate dashboards.
The v1 upgrade command is retained for v1-only installations; use the premium runner after
installing v2.

Premium features include native dashboard widgets, working capture/review tabs, account
and budget relations, native rollups, weighted grades, course workload, production blockers,
packaging and repurpose fields, honest habit modes, partial-payment tracking and scope guard.
Existing course/channel/habit/client/project pages gain contextual linked views only when
their body is empty. Existing user-authored bodies are preserved.

Original banners are saved under `assets/banners/*-v2.png`. `assets/banners/prompts.json`
records the exact prompts, built-in ImageGen mode and final saved paths. Images are uploaded
to Notion's own file service and attached as native page covers; no third-party image host
is required. Empty record covers receive the corresponding theme artwork for gallery cards.

`reports/premium-v2-result.json` records actual installed counts and review items. Chart
availability can depend on the workspace plan; a rejected optional number chart does not
prevent the operational tables, galleries, boards and calendars from being installed.
Relative date formulas keep current-month and Today views useful after the installation date.
Unmatched or ambiguous old labels are preserved for manual matching; no fuzzy financial or
client association is guessed.

Native button actions and recurring database templates require UI configuration according
to the current API documentation. The included capture tabs use Notion's functional New
control. No fake action buttons, automatic bank/YouTube connections, public sharing or client
messages are created.

Official references checked for v2:
- https://developers.notion.com/guides/data-apis/working-with-views
- https://developers.notion.com/reference/create-view
- https://developers.notion.com/reference/create-file
- https://developers.notion.com/reference/upload-file
- https://developers.notion.com/reference/property-object
# Client Desk visual correction (23 October 2026)

Client Desk now uses ordinary linked views and a collapsed reference library. Its original page ID and all five original sources/records are retained. See [the verified redesign report](reports/client-desk-v3-summary.md).

Signed-in testing exposed a v2 limitation: native dashboard widgets were accepted by the API but the workspace displayed “Upgrade to restore your dashboard.” API verification is not visual verification. The other four templates have not yet received the Client Desk correction.

Client Desk dry-run: `.venv\Scripts\python.exe -m app.premium.client_desk`. Preserve `state/client-desk-v3.json` and its backup pointer. Do not reset manifests to force an apply. Use `--apply --polish-only` for the scoped journaled polish after UI organization.


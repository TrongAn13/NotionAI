# Client Desk — signed-in visual redesign

The original Freelancer Business OS page is now **Client Desk**, at the same page ID. Discovery accepts both names.

## Why v2 looked unchanged

Signed-in inspection on 23 October 2026 showed “Upgrade to restore your dashboard”: the native dashboard view was gated by the workspace plan even though the API accepted its widgets. The earlier API audit did not establish that the interface rendered. The previous commercial-readiness claim was premature.

## Applied to Client Desk

- Full-width page with the existing original banner and a short brand title.
- Three colored navigation cards: Deliver, Collect and Grow. Each jumps to a real work area.
- Four ordinary linked modules: Focus desk, Delivery studio, Money desk and Next opportunities.
- Twelve list/table/gallery/calendar/board views, referencing the original five sources. No new dashboard or chart views.
- Project cover cards; title-first property ordering; hidden empty lead groups.
- Missing workflow choices added to the imported select fields, including Done, Completed, Paid, and Won/Lost. Existing option IDs, colors and record values retained.
- All previous content moved into a collapsed Reference library through the Notion UI. The old gated dashboard is retained there for reference, outside the working home.

## Verification

- Read-only audit: **103 existing blocks unchanged**, **5 existing records unchanged**, **5 original sources**, 12 unique ordinary views.
- Signed-in browser checked the task list, project gallery, invoice balances, payment-entry tab, scope tab, lead board and calendar. The sample task appears on 2 November 2026. No sample values were edited for testing.
- Desktop screenshots are saved under `reports/screenshots/`. A 390px desktop viewport exposed compressed navigation columns; it is recorded as a limitation, not a passed mobile test. Notion documents that its actual mobile app stacks columns, but that app has not been tested here: [Notion mobile layout](https://www.notion.com/help/notion-for-mobile).
- Buyer duplication, sales packaging and a full mobile-app test remain release tasks.

## Scope

This iteration changes Client Desk. The other four templates still need the same plan-compatible visual redesign. Their v2 native dashboards should not be described as visually verified or commercially ready.

## Recovery and reruns

Backup: `backups/snapshot-20261023T064254-d9174557.json`.

State: `state/client-desk-v3.json`; audit: `reports/client-desk-v3-audit.json`.

Dry run: `.venv\Scripts\python.exe -m app.premium.client_desk`.

The initial apply inserts the owned home. Library nesting and full width are UI operations. A rerun can stop on a changed navigation tree rather than overwrite edits. `--apply --polish-only` runs journaled view/typography polish without re-appending that tree. Keep state and backups; do not reset them to force a rerun.

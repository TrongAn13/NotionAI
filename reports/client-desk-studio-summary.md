# Client Desk · Design / Web Studio

Applied to the existing Client Desk page on 23 October 2026. This iteration develops the working template; seller identity, support information and publishing are deferred.

## Working product changes

- Native **Design / Web project** database template, set as the default for every Projects view. It includes the banner/icon and six editable sections: discovery brief, proposal/scope, change decisions, launch quality gate, handoff, and debrief.
- Native **Change request** database template, with Work Type = Change request and Decision = Requested. No client, fee, approval or payment is pre-agreed.
- Project pages open with content first; all properties remain accessible through View details.
- **Project intake** collects the outcome, success measure, approver, scope and asset readiness. Project Gate exposes the next missing preparation step.
- **Scope Guard / Change desk** appears on the home, the existing project and the reusable project template. Capture request is compact; Estimate & approval contains the detailed estimate/evidence fields.
- Approved fees/hours require the approved decision, reviewed estimate, approval-evidence URL and decision date. Declined/deferred/unconfirmed requests contribute zero. A recorded link is not a verified signature.
- **Change impact** shows approved extras, extra hours and pending decisions. Requests are excluded from the new delivery-completion calculation and Focus desk.
- Project-local deliveries and invoice views remain connected to the original sources. A new project template includes these scoped work areas too.
- Previous project notes are preserved in a collapsed reference section. The home includes a short first-project guide.

## Verified

- Read-only audit passed: **127 pre-existing blocks unchanged**, **5 original records and their original property values unchanged**, **5 original sources retained**.
- **16 new ordinary views**, all pointing to original sources; no native Business dashboard or chart dependency added.
- **7 live gate cases passed** on the native task template: estimate required, approval required, evidence required, approved, declined, deferred and decision-date required. Its defaults were restored afterward. No original customer/project values were used for these test estimates.
- A session-created empty page was isolated as QA, the native project template was applied, all six document sections appeared, and three Change desk filters retargeted to the new project. That QA page was moved to recoverable Trash after the check. No regular QA record remains in the active sources.
- Signed-in UI checked the native template editor/default menu, property panel, proposal tables, compact capture and estimate tab. Desktop screenshots are under `reports/screenshots/`.
- Mocked/unit suite: **47 tests passed**; Ruff clean.

## Release checks still open

Cross-workspace buyer duplication and the actual mobile app still need verification. The native-template application test above is not a cross-workspace duplication test. No public sale/duplication permissions were enabled.

The provided buyer guide is at `product/client-desk/BUYER-GUIDE.md`. It documents what is manual. The seller release checklist remains separate from the buyer's daily workflow.

## Recovery and reruns

Fresh pre-iteration backup: `backups/snapshot-20261023T070605-8bc8696b.json`.

Journal: `state/client-desk-studio.json`; original/new schemas, template/view IDs and explicit rejected/normalized operations are retained. Initial sibling formula creation was rejected by Notion, so dependencies were installed in separate patches. A zero-width marker dropped by Notion was reconciled on the existing introduction block rather than appended again.

Dry-run: `.venv\Scripts\python.exe -m app.premium.studio`.

Apply requires the saved backup/state. `--native-only` populates UI-identified database templates; `--polish-only` updates the existing ordinary views. Do not discard manifests or reset journals to force writes over edits.

Evidence: `reports/client-desk-studio-audit.json`, `reports/client-desk-studio-live-gates.json`, `reports/client-desk-studio-template-check.json`, and `state/client-desk-qa-page.json` for recoverable QA cleanup.

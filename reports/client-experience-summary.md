# Client Desk — Client Experience Studio

Implemented on 23 October 2026 after comparing paid products by Easlo, Webwork Foundry and Sara. Seller identity and publishing remain deferred.

## What changed

- Client Experience Studio is linked from the existing Client Desk home and the native Design / Web project template.
- A reusable blank client portal has independent Content inbox, Review room and Decision log sources. None relates to internal business sources or another client.
- A fictional Northstar portal has ten example records: four content requests, three review rounds/requests and three decisions. A separate worked-project page follows brief, scope, collection, review, extra work, delivery, invoicing and handoff. Financial amounts appear only as illustrative prose, not live business records.
- A native Notion duplicate was retained as **Your first client portal**, providing a blank independent starting copy.
- Portals have branded covers, three visual orientation cards and ordinary embedded working views. Underlying sources were moved into collapsed advanced sections using the Notion UI.
- The guide explains how to move an out-of-scope review request into internal Scope Guard. This remains a deliberate manual workflow. No automatic invoice, email, approval signature or task creation is claimed.

## Verification

- 50 unit/regression tests passed, including rejection of resource creation outside registered containers and portal source isolation checks.
- 12 live portal gate cases passed; all example values were restored afterward. Missing asset/date, unreviewed assets, optional assets and complete content were checked. Review decisions were checked with missing version, preview, reviewer or date, complete approval, pending feedback and superseded versions.
- Native same-workspace duplication passed: six copied views point to three new independent data sources; none points to the master sources. The copy has no records, relations or rollups.
- Original-source preservation passed against the fresh backup: 204 existing blocks, six existing records and five business sources unchanged. Recorded in `client-experience-preservation.json`.
- Browser checks cover actual populated views, source grouping, desktop layout and native duplicate creation.

## Remaining release checks

Cross-workspace buyer duplication, actual Notion mobile app and access from a separate guest account remain unverified. No public sharing or guest access was enabled. The broad template catalogue outside Client Desk was not upgraded by this iteration.

## Recovery

Backup pointer: `state/client-experience-backup.json`. Durable journal: `state/client-experience.json`. A Windows file-lock interruption during a journal replacement was reconciled against the complete saved temporary journal; the completed record was retained rather than recreated. Original and reconciled state were compared before proceeding.

The builder is scoped to this existing project and manifest. Do not remove its state to force a new run. A creation timeout stops for reconciliation instead of retrying blindly.

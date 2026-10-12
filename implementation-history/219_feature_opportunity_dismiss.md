# Prompt 219 - Dismiss Opportunities

## Objective
Let users dismiss an opportunity (with an optional reason saved to the follow-up trail) and undismiss it, mirroring the jobs dismiss pattern: `dismissed` flag, `PUT dismissed` endpoint, dialog with optional note, list toggle defaulting to hidden.

## Current State
- Jobs dismiss: `dismissed` Integer 0/1 (`job_006_add_dismissed.py`), `repo.set_dismissed` (`sa_job_repository.py:964`), `PUT /jobs/{id}/dismissed {dismissed, note?}` appending the note to job notes (`jobs_v2_router.py:767`), drawer `Dismiss`/`Undismiss` (`JobDetailDrawer.tsx:541`), `DismissDialog` with optional note (`jobs-v2/components/DismissDialog.tsx:24`). No dismiss domain events in jobs.
- Opportunities: `OpportunityService` (`opportunities/application/services/opportunity_service.py`), `PUT`-style detail endpoints returning full detail (`opportunities_router.py`), follow-up notes (`add_note` with server-stamped author), list with status/source/query filters (`sa_opportunity_repository.py`).

## Changes
1. Model `OpportunityModel.dismissed` Integer default 0; migration `opportunity_003` via autogenerate scoped to `opportunity`, tuned, single head, fresh-DB round-trip.
2. `OpportunityService.set_dismissed(id, dismissed, note=None, author="")`: 404 when missing; on dismiss with a note records a follow-up note titled `Dismissed`; returns presented detail. No new domain event (parity with jobs pin/dismiss flags).
3. API: `PUT /api/opportunities/{id}/dismissed` (`{dismissed, note?}` → full detail); list gains `dismissed` filter (`None` = all, mirroring jobs repo semantics).
4. Frontend: `dismissed` on types; `opportunityApi.setDismissed`; `useDismissOpportunity` (detail + list invalidation); `DismissOpportunityDialog` (title `Dismiss opportunity`, optional note, `Dismiss`/`Cancel`); drawer footer `Dismiss`/`Undismiss` button; toolbar `Show dismissed` toggle (default off → `dismissed=false` filter); widget wiring with toasts.
5. Docs: domain `opportunity.md` + `overview.md`, `docs/api/opportunities/README.md` + `API.md`, UX `page.md` (toolbar row) + `opportunity-detail.md` (button + dialog wireframe).

## Testing Requirements
- Backend: set/unset, note-on-dismiss creates a `Dismissed` follow-up note, undismiss clears flag, missing 404, list filter true/false/None; `./scripts/docker-test.sh backend`.
- Frontend: api test, dialog submit, drawer dismiss/undismiss flows, toolbar toggle; `tsc --noEmit` clean for touched files.

## Constraints
- Respect AGENTS.md rules 10, 11, 13 (dialog wireframe), 14 (autogenerate-first), 15 (no new FKs — none needed), 18 (Docker tests only).
- Wording: `Dismiss` / `Undismiss` / `Dismiss opportunity` / `Show dismissed` (jobs parity).

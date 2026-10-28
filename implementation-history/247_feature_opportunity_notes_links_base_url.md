# Prompt 247 - Feature: Opportunity Notes at Create + User Links + Base URL

## Objective

Bring opportunities to parity with jobs for optional context (see
`implementation-history/README.md`, reference `005_refactor_company_notes_and_links.md`):
- **Notes at creation** — `CreateOpportunityRequest` accepts optional initial notes
  (title + content), stored in the existing `opportunity_notes` trail with the
  authenticated user as author.
- **User links** — a user-managed titled-links collection (`opportunity_links`
  table) mirroring `opportunity_notes`: add/delete only, per-item delete button
  in the UI (rule 9). Distinct from the existing `PATCH /{id}/links` job/company
  record-linking endpoint.
- **Base URL** — nullable `opportunity.opportunities.base_url` column: the
  canonical source page of the opportunity (e.g. a LinkedIn post). Settable at
  create, editable later (`PATCH /{id}/base-url`), appended to the extracted
  URL pool during `process` so resolution can use it.

## Current state

- `apps/backend/opportunities/...` — follow-up notes already exist as a separate
  table + repo + service + API (`opportunity_notes`, `OpportunityNoteAdded/Deleted`);
  no link collection, no editable base URL (see `docs/domain/opportunities/opportunity.md`).
- Jobs pattern: JSON TEXT columns (`job.jobs.notes`/`links`, validator requires
  http(s) URLs) + optional notes/links on create (`apps/frontend/src/shared/components/NotesLinksInput.tsx`).
- In-flight sibling feature 246 ("Move to Jobs") shares the same files
  (`events.py`, service/router tests, domain docs); this change stays additive.

## Implementation steps

1. **DB migration** `opportunity_004_add_base_url_and_links` (alembic
   autogenerate first, then tune content): nullable `base_url` on
   `opportunity.opportunities`; new `opportunity.opportunity_links`
   (`id, opportunity_id FK@schema, title?, url, created_at, updated_at, user_id`
   + indexes) modeled 1:1 on `opportunity_notes`.
2. **Backend**: `base_url` in ORM model + mappers + aggregate dataclass;
   `OpportunityLinkModel` + `IOpportunityLinkRepository` +
   `SQLAlchemyOpportunityLinkRepository` (+ repo delete hard-deletes links);
   service: `create_manual(data, author)` ingests `notes`/`links`/`base_url`
   (idempotent duplicates ignore them), `add_link`/`delete_link` mirror notes
   (http(s) URL validation), `set_base_url`; `_extract` folds `base_url` into
   `extracted_urls`; events `OpportunityLinkAdded/OpportunityLinkDeleted`.
3. **API**: create request gains `base_url`/`notes`/`links` (http(s) validators,
   author stamped from auth); `POST /{id}/links` (201), `DELETE /links/{link_id}`
   (204), `PATCH /{id}/base-url`; detail response carries `base_url` + `links`.
4. **Frontend**: entity types/api/hooks for links + base URL;
   `OpportunityCreateDrawer` adds an optional Base URL field + notes/links
   input section; `OpportunityDetailDrawer` renders + edits base URL and the
   user Links collection (add + per-item delete).
5. **Docs**: domain (`events.md` link events, `opportunity.md`, `overview.md`),
   API (`docs/api/API.md`, `docs/api/opportunities/README.md`), UX
   (`page.md`, `opportunity-detail.md`, `README.md`, `DESIGN.md` — ASCII + Mermaid).

## Testing requirements

- Backend (Docker only, rule 18): service tests — create with notes/links/base_url,
  url validation, link add/delete, base-url set/clear (`test_opportunity_service.py`);
  router tests — create payload, link 201/422/404, base-url 200/422/404.
- Frontend: vitest `entities/opportunity/api.test.ts` for the new client calls.
- `./scripts/docker-test.sh backend` + `frontend`, plus `npm run lint` / `typecheck`.

## Constraints

- No cross-context FK (rule 15) — single schema `opportunity` FK only.
- EDD incremental (rule 16): link events documented + emitted via the collector,
  no pub/sub infra.
- Notes remain add/delete (immutable). Rule 1/2/10/11 unchanged (no provider
  calls, ORM only, per-context router, structlog).
- Version bump only at release time.

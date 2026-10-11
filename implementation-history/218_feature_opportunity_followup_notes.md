# Prompt 218 - Opportunity Follow-Up Notes

## Objective
Give each opportunity a follow-up trail: timestamped, titled notes recording later messages (recruiter replies, new details) for further assessment, managed from the detail drawer. Ownership follows auth best practice — the server stamps the author; clients cannot spoof it.

## Current State
- Opportunities context: `apps/backend/opportunities/` (service `application/services/opportunity_service.py`, router `presentation/api/opportunities_router.py:121`, schemas `presentation/api/schemas/opportunities.py:108`).
- Notes precedent: applications `NoteService` (`applications/application/services/note_service.py:18`) — immutable notes (add/delete, no edit), best-effort events; `ApplicationNoteModel` (`applications/infrastructure/models/application_model.py:71`); `POST /{id}/notes` + `DELETE /notes/{id}` (`applications_router.py:239`).
- Auth: routers resolve the user via `get_current_user` (`dependencies.py:14`); all tables carry `user_id` scoping.
- Frontend detail drawer: `features/opportunities/components/OpportunityDetailDrawer.tsx` with section pattern + `useDeleteOpportunity`-style hooks (`entities/opportunity/hooks.ts`); `useAuth` provides the display name (`widgets/sidebar/index.tsx:139`).

## Changes
1. Backend model `OpportunityNoteModel` (`opportunity.opportunity_notes`: FK within schema only, `title`, `content`, `author` display name, `user_id` scope, timestamps); mapper + `SQLAlchemyOpportunityNoteRepository` (create/get/list newest-first/delete); `IOpportunityNoteRepository` port.
2. `OpportunityService.add_note` (non-empty content; author passed by caller) + `delete_note`; events `OpportunityNoteAdded/Deleted` via the port; catalog in `docs/domain/opportunities/events.md`.
3. API: `POST /api/opportunities/{id}/notes` (201, body `{title?, content}`; router stamps `author=current_user.display_name`) and `DELETE /api/opportunities/notes/{note_id}` (204); detail response gains `notes` newest-first.
4. Migration `opportunity_002` via autogenerate scoped to the `opportunity` schema, tuned (schema guard, existence guard), single head, fresh-DB round-trip.
5. Frontend: entity `OpportunityNote` type + `addNote`/`deleteNote` api + hooks (detail invalidation); drawer "Follow-ups" section (list with title/author/date/content + delete; title input + textarea + Add button); tests for api/hooks/section.
6. Docs: `docs/domain/opportunities/opportunity.md`, `docs/api/opportunities/README.md`, `docs/ux/features/opportunities/opportunity-detail.md` (notes section in wireframe).

## Testing Requirements
- Backend: service add/delete/validation/events; API create/list-in-detail/delete/404s; `./scripts/docker-test.sh backend`.
- Frontend: entity api test; drawer notes section test (add + delete flows); `tsc --noEmit` clean for touched files.
- Migration verified before done: `alembic heads` (single), fresh-DB `upgrade head` + downgrade/upgrade round-trip.

## Constraints
- Respect AGENTS.md rules 1 (LLM untouched), 2, 3, 10, 11, 13 (wireframe for the drawer section), 14 (autogenerate-first migration), 15 (FK only within `opportunity` schema), 16 (events documented, in-memory), 18 (Docker tests only).
- Notes are immutable (no edit endpoint), author is server-stamped from auth, `user_id`-scoped like every other table.

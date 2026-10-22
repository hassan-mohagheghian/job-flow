# Add Company

## Purpose

The Add Company drawer imports a new company via `POST /api/companies` and,
when queued, processes it through the shared `ProcessingExecution` lifecycle
(`COMPANY_PROCESSING`). It is the company variant of the shared **Create Entity
drawer** (also used by the Add Job drawer, see
`docs/ux/features/jobs/add-job.md`).

The form follows this field order: **primary link → optional name → additional
links → optional notes**.

---

# Drawer Layout

```text
┌──────────────────────────────────────────────┐
│ + Add Company                                │
├──────────────────────────────────────────────┤
│                                              │
│ Primary Link *                               │
│ ┌───────────────────────────────┐            │
│ │ https://acme.example          │            │
│ └───────────────────────────────┘            │
│ Tip: a copied link is auto-filled from your clipboard. │
│ [Website]  [LinkedIn]                        │
│                                              │
│ Company Name (Optional)                      │
│ ┌───────────────────────────────┐            │
│ │ Acme GmbH                     │            │
│ └───────────────────────────────┘            │
│                                              │
│ Additional Links                  [+ Add]    │
│ (link list)                                  │
│                                              │
│ Notes                             [+ Add]    │
│ (note list)                                  │
│                                              │
│   [        Add        ] [ Add & Process (x) ]│
│                                              │
└──────────────────────────────────────────────┘
```

---

# Behavior

## Primary Link

The primary link is the main source for the company and is required. The URL is
typed into the input; URLs missing a scheme are prefixed with `https://`.

Every time the drawer opens, the Primary Link field is **cleared first**, then
the clipboard is read — if it holds a URL (matching `http(s)://…`), that URL is
pasted into the field, replacing any stale value — matching the Add Job drawer
behavior. An empty or non-URL clipboard is ignored silently (the field opens
empty).

The prefill is **not** suppressed after an Add — the clipboard is read fresh on
every open, so if the user copies another link and opens the drawer again, the
new link fills immediately (no need to open twice).

Every other field starts empty on **every** open: the Company Name, selected
primary title, Additional Links, Notes and any half-typed link/note drafts are
cleared, including after the programmatic close that follows a successful Add.
Only the clipboard URL can arrive pre-filled.

The **Primary Link** input is **auto-focused** when the drawer opens.

A title can be selected from the preset chips **Website** and **LinkedIn**.
Clicking a chip toggles it on/off. Only one primary title can be active.

## Company Name

Optional. If provided, the name is persisted with the company and shown in the
Companies list. If empty, the primary link URL is used as the display name.

## Additional Links

The `+ Add` toggle reveals URL + title inputs. Quick preset titles: LinkedIn,
Website, Careers, GitHub. If Website or LinkedIn is already selected as the
primary title, that chip is disabled in the additional-link selector. URLs
missing a scheme are prefixed with `https://`.

## Notes

Optional free-text notes. Each note is typed into the textarea and added with
the `+` button. Notes whose content starts with `http` are treated as URLs
(rendered as links). Notes can be removed before submit.

## Submit

Two actions are offered in the footer:

| Action      | Behavior                                       | State   |
| ----------- | ---------------------------------------------- | ------- |
| Add         | Adds the company to the list, no processing.   | Enabled |
| Add & Queue | Adds the company and queues it for processing. | Enabled |

`Add` posts `POST /api/companies` with:

```json
{
  "name": "Acme GmbH",
  "notes": [{ "content": "..." }],
  "links": [{ "url": "https://acme.example", "title": "Website" }],
  "source": "web",
  "queue": false
}
```

The backend creates a `company.companies` row with status `created` and
persists the name and URL notes. With `queue: false` the company is **not**
processed — it can be reprocessed later from the row/detail actions. When
`queue: true`, a `COMPANY_PROCESSING` `ProcessingExecution` is created and
enqueued, and the response includes `execution_id`.

## After Submit

- A success toast is shown.
- The companies-v2 list query is invalidated.
- The drawer closes.
- The entry appears in the Companies list (with processing status from
  `latest_processing_execution`).
- The Processing Drawer is **not** opened automatically (unlike the Job Create
  & Queue flow).

## Validation

Submit is disabled while:

- There is no primary link URL.

---

# Related Documents

- `docs/ux/features/companies/page.md`
- `docs/ux/flows/companies/browse-companies.md`
- `docs/ux/features/jobs/add-job.md` (job variant of the shared drawer)

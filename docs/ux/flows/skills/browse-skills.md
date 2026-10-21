# Browse Skills

## Purpose

How a user discovers, filters, and manages skills in the Skills workspace.

---

# Flow

```text
Open Skills page
        │
        ▼
Load first page (GET /api/skills/list, page_size=10)
        │
        ▼
┌─────────────────────────┐
│  Browse / Manage        │
│                         │
│  Search / Filter / Sort │
│  Scroll (infinite)      │
│  Open row → Detail      │
└────────────┬────────────┘
             │
             ▼
   ┌──────────────────┐   ┌──────────────────┐
   │  Detail Drawer   │   │  Add Skill Drawer│
   │  Edit / Delete   │   │                  │
   │  Referenced Jobs │   │  Name, Level,    │
   │  → Jobs page     │   │  Category, Roles │
   └──────────────────┘   └──────────────────┘
```

---

# Steps

## 1. Open the Skills page

The page mounts, calls `GET /api/skills/list` for the first page, and renders
the virtualized table.

## 2. Search

Typing in the search box (debounced 300ms) refetches the list with the `query`
parameter. Supported fields: name, role, path, alias.

## 3. Filter by category

Selecting a category in the toolbar refetches the list with the `category`
parameter (one of technical / engineering / professional / domain / career).

## 4. Sort

Clicking a sortable header (Name, Level, Demand, Confidence, Created, Mentions)
refetches with the chosen `sort` and `order`. Default: `mention_count desc`.

## 5. Scroll

Reaching the sentinel fetches the next page with the cursor. Rows append until
`has_more` is false.

## 6. Open skill details

Clicking a row opens the Skill Detail drawer. The `?skill=` URL parameter is
set, so the drawer survives a reload (deep-link).

## 7. Add a skill

The toolbar "Add Skill" button opens the Add Skill drawer. On success the new
skill appears at the top of the list.

## 8. Edit / Delete

From the detail drawer or row actions the user can edit or delete the skill.
Deletion requires confirmation (`ConfirmDialog`).

## 9. Manage aliases and merge duplicates

From the Edit drawer the user can add/remove aliases and merge a duplicate skill
into a canonical one (`docs/ux/flows/skills/merge-skills.md`). The Mentions
column shows how many job/company analyses reference each skill.

## 10. View referenced jobs

The Skill Detail drawer's **Referenced Jobs (n)** section lists the jobs that
mention the skill (`GET /api/skills/{id}/jobs`). Clicking a job navigates to the
Jobs page and opens that job's drawer (`/jobs?job=<id>`).

---

# Edge Cases

## Deep link

Opening `/skills?skill=42` opens the detail drawer for skill 42 on mount.

## Deleting the open skill

The detail and edit drawers close; the `?skill=` parameter is cleared.

## No skills

An empty list shows the "No skills yet" empty state with a hint to add one.

## Search with no matches

Rows disappear and the empty state shows; the Clear button in the toolbar
restores the full list.

## Invalid skill deep-link

The `?skill=` value does not match a loaded row; the list still renders and the
drawer stays closed.

---

# Related Documents

- `docs/ux/features/skills/page.md`
- `docs/ux/features/skills/skill-detail.md`
- `docs/ux/features/skills/add-skill.md`
- `docs/ux/features/skills/edit-skill.md`
- `docs/api/skills/list-skills.md`

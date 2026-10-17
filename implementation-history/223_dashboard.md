# Task: Implement a High-Performance Job Sources Dashboard in Job-Flow

## Objective

Design and implement a new **Dashboard** section in Job-Flow that provides a fast, well-designed overview of job sources (job boards and recruitment websites), their canonical URLs, and the number of job listings associated with each source.

The dashboard must be modular and extensible so that additional widgets and analytics can be added later without requiring a major redesign.

Do not start coding immediately. First inspect the existing codebase, understand its architecture and conventions, document your findings, and then implement the feature consistently with the existing project.

## 1. Inspect the Existing Project

Before making changes, inspect:

- Backend architecture, framework, API conventions, and service boundaries.
- Existing database models, migrations, constraints, and indexing strategy.
- The current job listing model and how jobs are ingested, updated, deduplicated, and deleted.
- How job boards, source URLs, external identifiers, and source metadata are currently represented.
- Frontend framework, routing, component structure, UI library, styling conventions, and existing dashboard components.
- Authentication, authorization, tenant isolation, and API error-handling conventions.
- Existing testing infrastructure, documentation structure, and development commands.
- Existing performance bottlenecks directly related to job-source tracking or dashboard queries.

Read the relevant implementation and tests before proposing a schema or architecture.

Do not introduce a new abstraction or dependency if the existing project already provides a suitable solution.

## 2. Document the Design Before Implementation

Create or update a feature design document in the project's existing documentation structure.

If no suitable documentation structure exists, use `docs/features/job-sources-dashboard.md`.

The document must include:

1. Current-state architecture and relevant existing models.
2. Requirements and acceptance criteria.
3. Proposed UI layout and low-fidelity wireframes.
4. Database schema changes and migration strategy.
5. Source identification and canonicalization rules.
6. API design, request/response examples, pagination, filtering, and sorting.
7. Frontend component structure and loading, empty, and error states.
8. Performance considerations and measurable performance targets.
9. Data consistency, concurrency, and failure-handling considerations.
10. Security, authorization, and tenant-isolation requirements.
11. Testing strategy.
12. Implementation decisions, trade-offs, and any assumptions.
13. Deployment, migration, rollback, and operational considerations.

Keep the document synchronized with the actual implementation. Update it if implementation reveals that the original design needs to change.

## 3. Dashboard UI/UX

Add a Dashboard entry to the existing navigation and follow the project's established visual design system.

The page should look polished, modern, clean, and professional. Reuse existing UI components where appropriate.

### 3.1 Summary widgets

Implement reusable metric cards for:

- Total job listings.
- Total unique job sources.
- Active job sources.
- Listings with unknown or unassigned sources, if applicable to the existing data model.

Use real backend data. Do not hardcode sample statistics in production.

If the existing project is multi-tenant, ensure all metrics respect the current user's authorized data scope.

### 3.2 Job-source distribution chart

Add a pie or doughnut chart showing the distribution of job listings across job sources.

Requirements:

- Sort sources by job count in descending order.
- Display only the top five sources individually by default.
- Group the remaining sources into an "Other" category.
- Include a legend, clear labels, counts, and percentages where the existing chart library supports them.
- Calculate percentages using a clearly documented denominator.
- Handle zero jobs and empty datasets gracefully.
- Provide accessible labels and an alternative textual summary.
- Keep the chart readable on mobile and desktop.
- Avoid fetching every job listing merely to calculate chart data.

If a doughnut chart fits the existing design system better, prefer it over a crowded pie chart.

The chart must use the same source definitions and counting rules as the table and summary widgets.

### 3.3 Job-sources table

Display a paginated table containing, at minimum:

- Source name.
- Canonical website URL.
- Job count.
- Active/inactive status, if supported by the model.
- Last job activity, if this information is available or can be derived efficiently.

Provide:

- Server-side pagination.
- Search by source name or normalized domain.
- Sorting by job count, source name, and last activity where supported.
- Clear loading, empty, and error states.
- Clickable links to canonical source websites.
- Responsive behavior for narrow screens.
- A clear indication of the current page and total result count.

Do not display invented or misleading website URLs.

Keep the table component reusable so that it can support additional source metadata in the future.

## 4. Data Model and Source Tracking

First determine whether the existing schema already has a reliable source entity or equivalent representation.

If an equivalent entity exists, extend and reuse it rather than introducing a duplicate model.

Otherwise, evaluate introducing a `job_sources` table with fields appropriate to the project, such as:

- `id`
- `name`
- `canonical_url`
- `normalized_domain`
- `is_active`
- `created_at`
- `updated_at`

Add a source reference to the existing job model where necessary, following the project's naming conventions.

Use foreign keys, appropriate uniqueness constraints, and indexes.

### Source identification

Define and implement a consistent method for identifying sources.

Consider:

- Hostname normalization.
- Case normalization and trailing dots.
- Common URL variants.
- `www` prefixes.
- Known subdomains and redirects.
- Tracking parameters and URL fragments.
- Distinguishing genuinely separate platforms that share infrastructure.
- Jobs whose source cannot be reliably identified.

Do not assume that every hostname or subdomain represents a distinct job board.

Do not rely on arbitrary substring matching for domain classification.

Prefer explicit, testable canonicalization rules and a maintainable mapping for known aliases.

Treat source identity separately from individual job URLs and source-specific external job identifiers.

If a source cannot be identified confidently, preserve the job and represent the source as unknown or unassigned according to the existing data model.

### Ingestion integration

When a new job is ingested:

1. Identify or resolve its source.
2. Reuse an existing source when appropriate.
3. Create a source only when it is genuinely new and the identification is sufficiently reliable.
4. Associate the job with the source.
5. Preserve the existing job deduplication behavior.
6. Ensure retries and concurrent ingestion do not create duplicate sources.
7. Handle updates, deletions, and source corrections consistently.

Use database transactions and existing concurrency patterns where appropriate.

Do not silently modify unrelated ingestion behavior.

### Historical data

Determine how existing jobs should be backfilled with source associations.

Implement an appropriate migration or backfill process if required.

For large datasets, avoid an unnecessarily long blocking migration. Consider a resumable or batched backfill where justified by the actual data volume and deployment model.

Document how unresolved historical records will be handled.

## 5. Performance and Statistics

The dashboard should load quickly and avoid unnecessary database work.

Inspect the existing dataset, query patterns, and database before choosing an optimization strategy.

Requirements:

- Do not load all job records into application memory to calculate counts.
- Use database-side aggregation and suitable indexes.
- Avoid N+1 queries.
- Avoid issuing a separate count query for every source.
- Reuse a consistent counting definition across dashboard widgets.
- Fetch only the columns required by each endpoint.
- Apply server-side pagination, filtering, and sorting.
- Avoid duplicate requests from frontend components where practical.
- Use the project's existing caching mechanisms only when beneficial.

### Aggregated statistics

Evaluate whether live aggregation is sufficiently fast.

Only introduce a dedicated statistics or counter table if measured query cost, dataset size, or workload justifies it.

If a materialized view, summary table, or counter cache is introduced, document:

- How it is updated.
- How concurrent writes are handled.
- How retries and duplicate events are prevented from corrupting counts.
- How updates and deletions affect statistics.
- How stale data is handled.
- How full reconciliation can repair discrepancies.

Do not add unnecessary infrastructure for a dashboard that can be served efficiently with indexed SQL queries.

Define a realistic performance target based on the existing environment, dataset size, and infrastructure. Measure the important queries and record the results. Do not claim performance improvements without evidence.

## 6. Backend API

Follow existing API conventions and authentication requirements.

Design appropriate endpoints for:

- Dashboard summary metrics.
- Job-source distribution.
- Paginated job-source listings.

These may be combined or separated depending on the existing architecture and measured performance needs.

The API should support relevant filters, sorting, pagination, and a documented response schema.

Validate query parameters, use consistent error responses, and prevent unauthorized access to other tenants' data.

Avoid overfetching and keep frontend contracts explicit.

Add or update API documentation using the project's existing documentation mechanism.

## 7. Frontend Architecture

Implement the dashboard using the current frontend framework, routing system, chart library, and design system.

Requirements:

- Reusable metric-card components.
- A reusable source-distribution chart.
- A reusable paginated source table.
- Typed API responses where supported.
- Clear loading, empty, error, and retry states.
- Sensible responsive layouts.
- Accessible interactions and semantic markup.
- Consistent formatting for numbers, URLs, dates, and percentages.

Avoid introducing a new charting or UI dependency unless the existing dependencies cannot reasonably meet the requirements.

Keep data fetching and presentation concerns appropriately separated.

Do not add unrelated features merely to make the dashboard appear more complete.

## 8. Testing

Add meaningful tests following the existing project conventions.

### Backend tests

Cover:

- Source normalization and canonicalization.
- Known aliases and subdomains.
- Unknown sources.
- Duplicate source prevention.
- Concurrent or repeated ingestion.
- Correct job counts.
- Job updates and deletions.
- Pagination, filtering, and sorting.
- Empty datasets.
- Dashboard statistics and chart aggregation.
- Authentication, authorization, and tenant isolation.
- Historical backfill behavior where applicable.

### Frontend tests

Cover:

- Rendering summary widgets with real API response shapes.
- Chart aggregation and the "Other" category.
- Pagination and sorting.
- Search and filtering.
- Loading, empty, and error states.
- Missing or unknown source data.
- Responsive and accessible behavior where the existing test setup supports it.

Run the relevant existing tests, the new tests, formatting, linting, type checks, and other project-standard validation commands.

Fix regressions introduced by this work.

Do not weaken, delete, or bypass existing tests to make the implementation pass.

## 9. Relevant Optimizations Only

You may improve existing code when the improvement is directly necessary for accurate source tracking, efficient dashboard queries, reliable ingestion, or consistency with the new functionality.

Examples include:

- Adding a missing database index.
- Removing an N+1 query affecting dashboard statistics.
- Improving source canonicalization used by ingestion.
- Fixing a directly related source-association bug.
- Improving pagination or query efficiency.
- Correcting a directly related data-consistency issue.

Before each broader optimization, explain the problem, evidence, proposed change, and risk.

Do not undertake unrelated refactoring, redesign unrelated pages, replace core frameworks, or introduce new infrastructure without a clear justification.

Keep changes small, reviewable, and backward-compatible wherever possible.

## 10. Implementation Workflow

Proceed in the following order:

1. Inspect the codebase and identify relevant files.
2. Write down the current-state findings and proposed design.
3. Create or update the feature documentation, including wireframes.
4. Identify schema and migration requirements.
5. Implement source identification and ingestion integration.
6. Implement database queries and backend APIs.
7. Implement the dashboard UI and its widgets.
8. Add tests and relevant performance measurements.
9. Run the project's validation commands.
10. Review the final diff for regressions, unnecessary changes, security issues, and undocumented behavior.
11. Update the documentation to reflect the final implementation.

If a critical design decision depends on missing information, investigate the existing code and choose a conservative, documented approach. Ask for clarification only when proceeding would create a substantial risk or require an irreversible decision.

Do not stop after producing a plan or wireframe. Complete the implementation when the available environment and permissions allow it.

Do not claim that a migration, test, build, or deployment succeeded unless it actually ran and its result was verified.

## 11. Definition of Done

The task is complete when:

- The Dashboard is accessible through the existing application navigation.
- The summary widgets display correct data from the backend.
- The chart accurately represents the top five sources plus "Other".
- The source table supports server-side pagination and relevant sorting and search.
- New job ingestion assigns sources reliably without creating duplicates.
- Existing data is handled through a documented backfill or migration strategy where required.
- Database queries are efficient and measured.
- Authorization and tenant isolation remain intact.
- Relevant automated tests pass.
- The feature documentation contains the wireframes, architecture decisions, schema, API contracts, performance findings, and operational instructions.
- Any directly related optimizations are documented.
- No unrelated changes or unsupported claims remain.

## Final Report

When finished, provide a concise implementation report containing:

1. Features implemented.
2. Files and components changed.
3. Database migrations and backfill steps.
4. API endpoints and example responses.
5. UI components and wireframe/documentation locations.
6. Performance optimizations and measured results.
7. Tests and validation commands executed, including failures.
8. Any known limitations, assumptions, or follow-up work.

Start by inspecting the existing Job-Flow repository and its documentation. Preserve the project's established conventions and make decisions based on the actual codebase rather than assumptions.

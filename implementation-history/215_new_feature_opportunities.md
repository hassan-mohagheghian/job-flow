Add a new feature to the existing job intelligence system: an "Inbound Opportunities" workflow.

Important: Do NOT redesign or replace the existing system. First understand the current architecture, domain models, scoring logic, candidate profile, rules, job/company entities, and application workflow. Reuse the existing components, services, schemas, and scoring mechanisms wherever possible.

## Goal

The current system mainly starts from Job Descriptions (JDs), analyzes jobs/companies, scores them against the candidate profile, and helps identify an application path.

We now need the reverse workflow:

Instead of starting with a JD, the user receives an inbound opportunity, for example through Gmail, LinkedIn, or another source. The user should be able to provide the message/email content, and the system should turn it into a structured opportunity, progressively enrich it with information, evaluate it against all existing candidate context and rules, assign a score, and identify the best next step for applying.

The feature should work even when the initial message contains very little information.

## Core workflow

Inbound message/email
↓
Create Inbound Opportunity
↓
Extract available information
↓
Identify company / role / job
↓
Enrich with existing system data
↓
Evaluate against candidate profile + rules
↓
Calculate Job/Opportunity Score
↓
Find application path
↓
Track status and next action

## Input

The user should be able to provide an inbound message manually, initially by pasting the email/message text.

The input should preserve the original content and metadata when available, such as:

- Source (Gmail, LinkedIn, manual, etc.)
- Sender
- Sender email
- Date
- Subject
- Raw message content
- URLs contained in the message

Design the model so that additional integrations can be added later without changing the core domain logic.

## New domain concept: Opportunity

Introduce an Opportunity/InboundOpportunity concept rather than immediately assuming that every inbound message represents a complete Job.

An inbound message may contain:

- A complete JD
- A short recruiter message
- Only a company name
- Only a job title
- A recruiter asking for a CV
- A link to a job
- A vague hiring message
- An opportunity that cannot yet be identified

Therefore, the initial Opportunity must be allowed to be incomplete.

Suggested conceptual fields:

- id
- source
- source_message_id (nullable)
- sender information
- received_at
- subject
- raw_content
- extracted_information
- company_id (nullable)
- job_id (nullable)
- score
- evaluation
- status
- application_path
- next_action
- created_at
- updated_at

Adapt this to the existing architecture instead of blindly implementing these exact fields.

## Extraction

Create an extraction step that analyzes the inbound message and extracts whatever information is available.

Possible extracted information:

- Company
- Job title
- Job URL
- JD
- Recruiter/person
- Location
- Remote/hybrid/on-site
- Employment type
- Salary
- Required skills
- Experience requirements
- Visa/sponsorship information
- Work authorization requirements
- Contact information
- Application instructions

Extraction must be partial and tolerant of missing information.

Do not fabricate missing information.

Represent uncertainty explicitly, for example:

- known
- unknown
- inferred
- needs verification

## Entity resolution

After extraction, attempt to match the opportunity against existing entities.

For example:

- Existing Company
- Existing Job
- Existing recruiter/contact
- Existing opportunity
- Previous application

Avoid creating duplicates.

If the company already exists, link to it.

If the job already exists, link the Opportunity to the existing Job.

If the opportunity is actually a duplicate of an existing opportunity, merge or associate it instead of creating unnecessary duplicates.

## Enrichment

The system should progressively enrich the Opportunity.

For example:

Initial email:

    "Hi Hassan, we are hiring a Senior Backend Engineer.
     Would you be interested?"

Initial state:

    Company: Unknown
    Role: Senior Backend Engineer
    JD: Unknown
    Score: Partial / Pending

After identifying the company:

    Company: X
    Role: Senior Backend Engineer

After finding the JD:

    Skills: Python, Django, PostgreSQL, AWS
    Location: Germany
    Employment: Full-time

After evaluating eligibility:

    Armenia-compatible: Unknown
    Sponsorship: Unknown
    Technical match: High

The Opportunity should be re-evaluated when meaningful new information becomes available.

## Candidate context

The evaluation must use the existing candidate profile and all relevant information already available in the system.

Do NOT create a second candidate-profile system.

Reuse the existing:

- Skills
- Experience
- Seniority
- Preferred roles
- Preferred locations
- Remote/on-site/hybrid preferences
- Employment preferences
- Salary expectations
- Work authorization constraints
- Relocation preferences
- Career goals
- Existing personal rules
- Existing job/company history
- Existing scoring logic

The candidate context should be treated as the source of truth.

## Evaluation

For every Opportunity, produce a structured evaluation.

The evaluation should answer:

1. How technically well does the opportunity match the candidate?
2. Does the seniority match?
3. Does the location match?
4. Does the employment type match?
5. Does the salary match, if known?
6. Are there work authorization or sponsorship issues?
7. How well does it match the candidate's career direction?
8. What important requirements are missing?
9. What information is still unknown?
10. Is there enough information to apply?
11. What should the candidate do next?

Use the existing scoring/rules engine where possible.

Do not create arbitrary scoring logic if equivalent logic already exists.

If the current scoring system supports explainability, expose the same reasoning mechanism here.

## Score

Every Opportunity should have a score when enough information exists.

The score should be based on the same candidate/job evaluation principles already used by the existing system.

The UI should show both:

- Overall score
- Reasons behind the score

For example:

    Overall Match: 84

    Technical Match: 88
    Experience Match: 92
    Location: 75
    Career Alignment: 95

    Potential Issues:
    - AWS hands-on experience appears important
    - Sponsorship is unclear

Do not invent values just to fill the UI.

If there is insufficient information, explicitly show:

    Evaluation: Pending
    Reason: Job location and requirements are unknown

## Application path

The system should determine how the user can proceed.

Possible application paths include:

- Apply directly through a job URL
- Apply through the company's careers page
- Contact the recruiter
- Reply to the email
- Ask recruiter for the JD
- Ask recruiter about location/work authorization
- Research the opportunity first
- No actionable application path yet

The application path should be generated from the actual available information.

Do not invent URLs or application methods.

## Opportunity lifecycle

Implement a clear lifecycle, compatible with the existing status conventions.

For example:

    New
    ↓
    Extracted
    ↓
    Enriching
    ↓
    Evaluated
    ↓
    Ready to Apply
    ↓
    Applied
    ↓
    Replied / Interview / Rejected / Closed

Use the project's existing status conventions if they already exist.

## UI

Add an Inbound Opportunities section to the existing application.

The user should be able to:

1. Add a new inbound message.
2. See all inbound opportunities in chronological/order-of-relevance order.
3. Open an opportunity.
4. See the original message.
5. See extracted information.
6. See linked company/job.
7. See the current evaluation.
8. See the score and reasons.
9. See missing/unknown information.
10. See the recommended next action.
11. See the application path.
12. Update/reprocess the opportunity when new information is available.

Example list:

    #   Opportunity                  Source   Score   Status
    1   Senior Backend Engineer      Gmail    91      Ready to Apply
    2   Python Backend Engineer      Gmail    78      Review
    3   Software Engineer            LinkedIn 64      Needs Info

The ordering must be configurable or compatible with the existing sorting/filtering architecture.

## Progressive updates

The system should support reprocessing.

For example:

Day 1:
Recruiter email received
→ role identified
→ company unknown
→ evaluation incomplete

Day 2:
Company identified
→ enrich opportunity
→ re-evaluate

Day 3:
JD found
→ extract requirements
→ re-score

The system should preserve useful history rather than silently overwriting important previous evaluations.

## Architecture requirements

Before implementing:

1. Inspect the existing codebase.
2. Identify the current Job, Company, Candidate, scoring, rules, application, and ingestion models/services.
3. Reuse existing abstractions.
4. Avoid duplicating business logic.
5. Follow the project's current naming, architecture, validation, persistence, API, and UI conventions.
6. Add tests consistent with the existing testing strategy.
7. Keep the feature modular so future integrations such as Gmail/LinkedIn can feed the same Opportunity pipeline.

Do not introduce unnecessary infrastructure.

## API / backend

Add the minimum APIs required for:

- Creating an inbound opportunity
- Listing opportunities
- Retrieving an opportunity
- Updating/reprocessing an opportunity
- Triggering extraction/enrichment/evaluation
- Linking an opportunity to an existing Job/Company
- Updating its lifecycle/application status

Follow the existing API conventions.

## Important edge cases

Handle:

- Missing company
- Missing job title
- Missing JD
- Multiple jobs mentioned in one email
- Duplicate emails
- Duplicate opportunities
- Existing Job already in the database
- Existing Company already in the database
- Recruiter contacting the candidate without a specific job
- Job link without a JD
- Unsupported/unknown source
- Conflicting information
- Insufficient information for scoring

Never fabricate missing job/company information.

## Deliverables

Implement this feature end-to-end in the existing project.

Before coding, briefly document:

1. Existing architecture relevant to this feature.
2. Where the new Opportunity concept should integrate.
3. Which existing components will be reused.
4. Any schema/model changes required.
5. API/UI changes required.

Then implement the feature.

After implementation, provide:

- Files changed
- Main architectural decisions
- New data models/schemas
- New API endpoints
- UI changes
- Scoring/evaluation integration
- Tests added
- Any remaining limitations or TODOs

Most importantly: integrate this feature into the existing system instead of building a parallel job-management system.

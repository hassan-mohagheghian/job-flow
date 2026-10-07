# Project Context

## What This Project Solves

Job Search Intelligence is an AI-powered career platform that helps software engineers find and apply for jobs, especially visa-sponsored roles in Europe (Germany, Netherlands). It automates the job search workflow: discovering jobs, analyzing companies, managing skills, and providing career insights.

## Target Users

- Software engineers seeking visa-sponsored positions in Europe
- Career changers who need data-driven skill gap analysis
- Job seekers who want data-driven application insights

## Core Concepts

- **Job Processing Pipeline**: URL → fetch → extract → AI analysis → score → save. Runs as a single `ProcessingExecution` over **two LangGraph phases**: (1) an LLM-free context preparation phase (fetch, extract, build, validate, persist) and (2) a Job Analysis phase that performs **one combined LLM call** (`job.analyze`) extracting fields, scores, recommendation, summary, and tagged skills, then persists the result.
- **Job Analysis**: Canonical output stored in the `job.job_analysis` table — full payload, fit/success/overall scores, apply/consider/skip recommendation, apply reason, summary, matched/missing/low skill tags, and insights. Exposed through the Job Details drawer (`GET /api/jobs/{id}` → `analysis` block).
- **Company Intelligence**: Profile extraction, visa assessment, Fit/Success/Overall scoring
- **Skills Management**: 5-category taxonomy, aliases, AI-powered insights
- **Career Insights**: Health score, market analysis, opportunity funnel
- **Candidate Profile**: Upload a resume or LinkedIn profile as analysis input (masked PII); sources converge into a canonical candidate profile used as job-analysis context
- **Application Workspace**: Turn a job into a tracked application (status, applied date, follow-ups) and generate a tailored resume, cover letter and a job-preparation roadmap from the existing intelligence

## Key Rules

1. **Provider abstraction**: All AI calls go through LLMService — never call providers directly. Default provider is Mimo CLI, but OpenAI and local LLMs are supported via `AI_PROVIDER` env var
2. **TypeScript frontend**: All client code is `.ts`/`.tsx`
3. **SQLAlchemy ORM**: Use SQLAlchemy for all database access, never raw SQL
4. **Feature-based architecture**: Frontend organized by `features/`, `shared/`, `layout/`
5. **Single generation lock**: Only one AI analysis runs at a time
6. **URL uniqueness**: Base URL without query params for deduplication
7. **Hard delete for processed jobs**: `DELETE FROM jobs` + related tables
8. **All cards must have delete button**
9. **Default sort**: Newest first (`created_at desc`)
10. **Save folder paths configurable via .env**
11. **DDD/OOP/SOLID/TDD**: Follow domain-driven design, OOP, SOLID principles, and test-driven development

## System Boundaries

- **In scope**: Job discovery, company analysis, skill management, candidate profile (resume/LinkedIn input), career insights, job application workspace (tracking + artifact generation), inbound opportunities (message → extract → resolve → evaluate → track)
- **Out of scope**: Job application submission, interview scheduling, salary negotiation
- **External integrations**: AI Agent Layer (LLMService + provider abstraction), LinkedIn (scraping), job boards (URL fetching)

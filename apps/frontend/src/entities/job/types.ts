export interface Job {
  company: string
  role: string
  location: string
  score: string
  match: string
  overall_score: number | null
  fit_score: number | null
  success_score: number | null
  stack: string
  visa: string
  work_types: string[]
  employment_types: string[]
  posted_at: string | null
  created_at: string
  applicants: string | null
  locations: string | null
  linked_company: string | null
  status: string
  current_node: string | null
  progress_pct: number
  error: string | null
  [key: string]: any
}

export interface JobAgg {
  total: number
  high_match: number
  apply_now: number
  remote: number
  [key: string]: number
}

export interface JobTimelineDay {
  date: string
  count: number
}

export interface JobTimeline {
  days: JobTimelineDay[]
  total: number
}

export interface JobWithLocations extends Job {
  parsedLocations: string[]
}

export interface JobsResponse {
  jobs: Job[]
  total: number
  agg: JobAgg
}

export type SortField = 'created_at' | 'overall_score' | 'fit_score' | 'success_score' | 'company' | 'location' | 'applicants' | 'posted_at' | 'apply_time' | 'response_time'

export interface Scores {
  overall: number | null
  fit: number | null
  success: number | null
}

export interface ProcessingExecution {
  id: string
  status: ProcessingStatus
  started_at: string | null
  finished_at: string | null
}

export type ProcessingStatus = 'created' | 'queued' | 'starting' | 'running' | 'completed' | 'failed' | 'cancelled'

export type ProcessingStatusFilter = ProcessingStatus | 'none' | ''

export type RecommendationFilter = 'apply' | 'consider' | 'skip'

export type CreatedDateFilter = 'today' | 'yesterday' | 'week' | 'month' | ''

export interface JobSummary {
  id: string
  title: string | null
  company: string | null
  company_id: string | null
  company_type: string | null
  location: string | null
  visa: string | null
  salary: string | null
  employment_types: string[] | null
  work_types: string[] | null
  overall_score: number | null
  fit_score: number | null
  success_score: number | null
  rank: number | null
  tracking_status: string | null
  url: string | null
  updated_at: string | null
}

export type TrackingStatus =
  | 'not_applied'
  | 'seen'
  | 'preparing'
  | 'ready_to_apply'
  | 'applied'
  | 'interview'
  | 'offer'
  | 'accepted'
  | 'rejected'
  | 'withdrawn'
  | 'expired'

export type TrackingStatusFilter = TrackingStatus

export interface JobListItem {
  id: string
  title: string
  company_name: string
  location: string
  remote: boolean | null
  visa_sponsorship: boolean | null
  job_status: string
  latest_processing_execution: ProcessingExecution | null
  scores: Scores
  recommendation: string | null
  pinned: boolean
  dismissed: boolean
  tags: string[]
  rank: number | null
  tracking_status: TrackingStatus | null
  easy_apply: boolean | null
  updated_at: string | null
  created_at: string
}

export function getProcessingStatus(job: JobListItem): ProcessingStatus | null {
  return job.latest_processing_execution?.status ?? null
}

export interface JobSearchQuery {
  page?: number
  page_size?: number
  cursor?: string
  query?: string
  company_id?: string
  processing_status?: ProcessingStatus | 'none'
  location?: string
  remote?: boolean
  visa?: boolean
  overall_score_min?: number
  overall_score_max?: number
  fit_score_min?: number
  fit_score_max?: number
  success_score_min?: number
  success_score_max?: number
  pinned?: boolean
  dismissed?: boolean
  tags?: string
  recommendation?: RecommendationFilter[]
  tracking_status?: TrackingStatusFilter[]
  created_date?: CreatedDateFilter
  sort?: string
  order?: 'asc' | 'desc'
}

export interface JobSearchResult {
  items: JobListItem[]
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
  }
  cursor_pagination?: {
    total_items: number
    next_cursor: string | null
    has_more: boolean
  }
}

export interface InfiniteJobSearchResult {
  items: JobListItem[]
  next_cursor: string | null
  has_more: boolean
  total_items: number
}

export interface JobDetailWorkflowStep {
  id: string
  title: string
  status: string
  progress: number | null
  displayable: boolean
  children: JobDetailWorkflowStep[]
  error: { code: string; message: string } | null
  started_at: string | null
  completed_at: string | null
}

export interface JobDetailWorkflow {
  id: string
  name: string
  status: string
  current_step: JobDetailWorkflowStep | null
  progress: number | null
  steps: JobDetailWorkflowStep[]
}

export interface JobDetailExecution {
  execution_id: string
  status: string
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  error: { message: string } | null
  current_step: string | null
  workflow: JobDetailWorkflow | null
}

export interface JobNoteItem {
  title?: string | null
  content: string
}

export interface JobLinkItem {
  title?: string | null
  url: string
}

export interface JobAnalysisScoresExplanation {
  fit_factors: string[]
  success_factors: string[]
  concerns: string[]
}

export interface JobAnalysisSummary {
  summary: string
  resume_fit: string
  note: string
}

export interface JobAnalysisSkill {
  name: string
  category: string | null
  level: number | null
  status: string | null
  evidence: string | null
}

export interface JobAnalysis {
  recommendation: string | null
  apply_reason: string | null
  scores_explanation: JobAnalysisScoresExplanation | null
  summary: JobAnalysisSummary | null
  skills: JobAnalysisSkill[]
  insights: string[]
  generated_at: string | null
}

export interface RelatedCompany {
  company_id: string
  name: string | null
  role: string | null
  company_type: string | null
  confidence: number | null
  reason: string | null
}

export interface JobDetail {
  id: string
  title: string | null
  company_name: string | null
  company_id?: string | null
  company_type?: string | null
  role: string | null
  location: string | null
  work_types: string[] | null
  employment_types: string[] | null
  salary: string | null
  visa: string | null
  url: string | null
  status: string | null
  rank: number | null
  scores: Scores
  latest_processing_execution: JobDetailExecution | null
  analysis: JobAnalysis | null
  related_companies: RelatedCompany[]
  description: string | null
  notes: JobNoteItem[]
  links: JobLinkItem[]
  tags: string[]
  tracking_status: TrackingStatus | null
  easy_apply: boolean | null
  updated_at: string | null
  created_at: string | null
}

export interface JobEditInput {
  title?: string | null
  role?: string | null
  company?: string | null
  location?: string | null
  url?: string | null
  work_types?: string[] | null
  employment_types?: string[] | null
  visa?: string | null
  salary?: string | null
  description?: string | null
  notes?: JobNoteItem[]
  links?: JobLinkItem[]
  tags?: string[]
}

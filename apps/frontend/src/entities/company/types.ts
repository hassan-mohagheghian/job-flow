import type { ProcessingExecution } from '@/entities/job/types'

export interface CompanyScores {
  overall: number | null
  fit: number | null
  success: number | null
  overall_grade: string | null
}

export interface CompanyProcessing {
  status: string | null
  current_node: string | null
  progress_pct: number | null
  error: string | null
}

export interface CompanyMainRef {
  id: string
  name: string
}

export interface CompanyListItem {
  id: string
  name: string
  industry: string | null
  city: string | null
  country: string | null
  company_size: string | null
  company_type: string | null
  logo_url: string | null
  website: string | null
  description: string | null
  job_count: number
  recruiter_job_count: number
  scores: CompanyScores | null
  processing: CompanyProcessing | null
  latest_processing_execution: ProcessingExecution | null
  parent_company_id: string | null
  main_company: CompanyMainRef | null
  alias_count: number
  is_alias: boolean
  pinned: boolean
  updated_at: string | null
  created_at: string | null
}

export type CompanySortField = 'created_at' | 'updated_at' | 'name' | 'overall_score' | 'fit_score' | 'success_score'

export interface CompanySearchQuery {
  page_size?: number
  cursor?: string
  query?: string
  industry?: string
  company_type?: string
  status?: string
  pinned?: boolean
  sort?: string
  order?: 'asc' | 'desc'
}

export interface InfiniteCompanySearchResult {
  items: CompanyListItem[]
  next_cursor: string | null
  has_more: boolean
  total_items: number
}

export interface CompanyIntelligenceScores {
  fit?: number | null
  success?: number | null
  overall?: number | null
  overall_grade?: string | null
  fit_grade?: string | null
  [key: string]: unknown
}

export interface CompanyIntelligence {
  overview?: Record<string, unknown> | null
  culture_analysis?: Record<string, unknown> | null
  international_analysis?: Record<string, unknown> | null
  career_analysis?: Record<string, unknown> | null
  benefits_analysis?: Record<string, unknown> | null
  visa_analysis?: Record<string, unknown> | null
  technology_analysis?: Record<string, unknown> | null
  recommendation?: Record<string, unknown> | null
  scores?: CompanyIntelligenceScores | null
  generated_at?: string | null
  [key: string]: unknown
}

export interface CompanyNote {
  id: number
  content: string
  created_at?: string | null
}

export interface CompanyLink {
  id: number
  url: string | null
  title: string | null
  description: string | null
  status: string | null
  created_at?: string | null
}

export interface CompanyLinkedJob {
  id: string
  role: string | null
  location: string | null
  match: string | null
  score: string | null
  fit_score: number | null
  success_score: number | null
  overall_score: number | null
  rank: number | null
}

export interface RecruiterJobRef {
  id: string
  title: string | null
  location: string | null
}

export interface RecruiterForCompany {
  company_id: string
  name: string | null
  job_count: number
  jobs: RecruiterJobRef[]
}

export interface CompanyDetail {
  id: string
  name: string
  industry?: string | null
  city?: string | null
  country?: string | null
  website?: string | null
  description?: string | null
  company_size?: string | null
  company_type?: string | null
  logo_url?: string | null
  founded_year?: string | null
  job_count?: number
  status?: string | null
  current_node?: string | null
  progress_pct?: number | null
  error?: string | null
  notes?: CompanyNote[]
  links?: CompanyLink[]
  intelligence?: CompanyIntelligence | null
  scores?: CompanyScores | null
  jobs?: CompanyLinkedJob[]
  recruiter_job_count?: number
  recruiter_for?: RecruiterForCompany[]
  recruiter_jobs?: CompanyLinkedJob[]
  parent_company_id?: string | null
  main_company?: CompanyMainRef | null
  alias_count?: number
  is_alias?: boolean
  pinned?: boolean
  created_at?: string | null
  updated_at?: string | null
  [key: string]: unknown
}

export interface CompanyMainRequest {
  main_company_id: string | null
}

export interface CompanyEditInput {
  name?: string | null
  industry?: string | null
  city?: string | null
  country?: string | null
  website?: string | null
  description?: string | null
  company_size?: string | null
  company_type?: string | null
  notes?: unknown
  links?: unknown
}



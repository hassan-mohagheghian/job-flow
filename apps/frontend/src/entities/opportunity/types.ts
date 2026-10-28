export type OpportunitySource = 'manual' | 'gmail' | 'linkedin'

export type OpportunityStatus =
  | 'new'
  | 'extracted'
  | 'enriching'
  | 'needs_info'
  | 'evaluated'
  | 'ready_to_apply'
  | 'applied'
  | 'replied'
  | 'interview'
  | 'rejected'
  | 'closed'

export type EvaluationStatus = 'pending' | 'complete'

export interface OpportunityListItem {
  id: string
  title: string
  company_name: string | null
  job_title: string | null
  source: OpportunitySource
  status: OpportunityStatus
  evaluation_status: EvaluationStatus
  dismissed: boolean
  overall_score: number | null
  fit_score: number | null
  success_score: number | null
  recommendation: string | null
  next_action: string | null
  job_id: string | null
  company_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface OpportunityListQuery {
  status?: OpportunityStatus | ''
  source?: OpportunitySource | ''
  dismissed?: boolean
  query?: string
  limit?: number
  offset?: number
}

export interface OpportunityListResult {
  items: OpportunityListItem[]
  total: number
}

export interface OpportunityEvaluationSnapshot {
  id: string
  opportunity_id: string
  status: OpportunityStatus
  evaluation_status: EvaluationStatus
  fit_score: number | null
  success_score: number | null
  overall_score: number | null
  recommendation: string | null
  snapshot: Record<string, unknown>
  created_at: string | null
}

export interface OpportunityNote {
  id: string
  opportunity_id: string
  title: string | null
  content: string
  author: string
  created_at: string | null
  updated_at: string | null
}

export interface OpportunityLink {
  id: string
  opportunity_id: string
  title: string | null
  url: string
  created_at: string | null
  updated_at: string | null
}

export interface OpportunityDetail extends OpportunityListItem {
  source_message_id: string | null
  sender: string | null
  sender_email: string | null
  received_at: string | null
  subject: string | null
  raw_content: string
  extracted_urls: string[]
  extracted: Record<string, any>
  evaluation: Record<string, any>
  missing_information: string[]
  application_path: Record<string, any>
  duplicate: boolean
  base_url: string | null
  created_job?: boolean
  evaluations: OpportunityEvaluationSnapshot[]
  notes: OpportunityNote[]
  links: OpportunityLink[]
}

export interface CreateOpportunityRequest {
  source?: OpportunitySource
  source_message_id?: string | null
  sender?: string | null
  sender_email?: string | null
  received_at?: string | null
  subject?: string | null
  raw_content: string
  base_url?: string | null
  notes?: CreateOpportunityNoteRequest[]
  links?: CreateOpportunityLinkRequest[]
}

export interface UpdateOpportunityLinksRequest {
  job_id?: string | null
  company_id?: string | null
}

export interface CreateOpportunityLinkRequest {
  title?: string | null
  url: string
}

export interface UpdateOpportunityBaseUrlRequest {
  base_url: string | null
}

export interface CreateOpportunityNoteRequest {
  title?: string | null
  content: string
}

export type ApplicationStatus =
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

export type ApplicationDocumentType = 'tailored_resume' | 'cover_letter'

export type ApplicationArtifactType = 'roadmap' | ApplicationDocumentType

export interface ApplicationFollowUp {
  id: string
  application_id: string
  scheduled_at: string | null
  note: string
  completed_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ApplicationStatusEvent {
  id: string
  application_id: string
  status: ApplicationStatus
  changed_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ApplicationNote {
  id: string
  application_id: string
  content: string
  created_at: string | null
  updated_at: string | null
}

export interface ApplicationDocument {
  id: string
  application_id: string
  document_type: ApplicationDocumentType
  version: number
  content: string
  created_at: string | null
  updated_at: string | null
}

export interface ApplicationDetail {
  id: string
  job_id: string
  status: ApplicationStatus
  applied_at: string | null
  created_at: string | null
  updated_at: string | null
  status_timeline: ApplicationStatusEvent[]
  follow_ups: ApplicationFollowUp[]
  notes: ApplicationNote[]
  documents: ApplicationDocument[]
}

export interface GenerateResponse {
  execution_id: string
  status: string
  artifact: ApplicationArtifactType
}

export interface DeleteResponse {
  status: string
}

export interface UpdateApplicationInput {
  status?: ApplicationStatus
  applied_at?: string | null
  timeline_at?: string | null
}

export interface CreateFollowUpInput {
  scheduled_at?: string | null
  note?: string
}

export interface UpdateFollowUpInput {
  scheduled_at?: string | null
  note?: string
  completed?: boolean
}

export interface CreateNoteInput {
  content: string
}

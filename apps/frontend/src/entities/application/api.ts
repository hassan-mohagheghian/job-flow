import { api } from '@/shared/api'
import type {
  ApplicationDetail,
  ApplicationDocument,
  ApplicationDocumentType,
  ApplicationFollowUp,
  ApplicationNote,
  ApplicationStatusDistribution,
  ApplicationStatusEvent,
  CreateFollowUpInput,
  CreateNoteInput,
  DeleteResponse,
  GenerateResponse,
  UpdateApplicationInput,
  UpdateFollowUpInput,
} from './types'

export const applicationApi = {
  getByJob: (jobId: string) => api.get<ApplicationDetail>(`/applications/by-job/${jobId}`),
  get: (applicationId: string) => api.get<ApplicationDetail>(`/applications/${applicationId}`),
  statusDistribution: () =>
    api.get<ApplicationStatusDistribution>(`/applications/status-distribution`),
  create: (jobId: string, seenAt?: string | null) =>
    api.post<ApplicationDetail>(`/applications`, { job_id: jobId, seen_at: seenAt ?? null }),
  update: (applicationId: string, data: UpdateApplicationInput) =>
    api.patch<ApplicationDetail>(`/applications/${applicationId}`, data),
  updateTimeline: (eventId: string, changedAt: string | null) =>
    api.patch<ApplicationStatusEvent>(`/applications/timeline/${eventId}`, { changed_at: changedAt }),
  deleteTimeline: (eventId: string) =>
    api.delete<void>(`/applications/timeline/${eventId}`),
  addFollowUp: (applicationId: string, input: CreateFollowUpInput) =>
    api.post<ApplicationFollowUp>(`/applications/${applicationId}/follow-ups`, input),
  updateFollowUp: (followUpId: string, input: UpdateFollowUpInput) =>
    api.patch<ApplicationFollowUp>(`/applications/follow-ups/${followUpId}`, input),
  deleteFollowUp: (followUpId: string) =>
    api.delete<void>(`/applications/follow-ups/${followUpId}`),
  addNote: (applicationId: string, input: CreateNoteInput) =>
    api.post<ApplicationNote>(`/applications/${applicationId}/notes`, input),
  deleteNote: (noteId: string) =>
    api.delete<void>(`/applications/notes/${noteId}`),
  generateRoadmap: (applicationId: string) =>
    api.post<GenerateResponse>(`/applications/${applicationId}/roadmap/generate`),
  generateDocument: (applicationId: string, documentType: ApplicationDocumentType) =>
    api.post<GenerateResponse>(`/applications/${applicationId}/documents/${documentType}/generate`),
  updateDocument: (documentId: string, content: string) =>
    api.patch<ApplicationDocument>(`/applications/documents/${documentId}`, { content }),
  deleteDocument: (documentId: string) =>
    api.delete<DeleteResponse>(`/applications/documents/${documentId}`),
  downloadPdf: async (documentId: string, filename: string): Promise<void> => {
    const blob = await api.download(`/applications/documents/${documentId}/pdf`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}

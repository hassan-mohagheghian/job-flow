import { api } from '@/shared/api'
import type {
  CreateOpportunityRequest,
  OpportunityDetail,
  OpportunityListQuery,
  OpportunityListResult,
  OpportunityStatus,
  UpdateOpportunityLinksRequest,
} from './types'

export const opportunityApi = {
  create: (data: CreateOpportunityRequest) =>
    api.post<OpportunityDetail>('/opportunities', data),
  list: (query: OpportunityListQuery = {}) => {
    const params = new URLSearchParams()
    if (query.status) params.set('status', query.status)
    if (query.source) params.set('source', query.source)
    if (query.query) params.set('query', query.query)
    if (query.limit !== undefined) params.set('limit', String(query.limit))
    if (query.offset !== undefined) params.set('offset', String(query.offset))
    const suffix = params.toString()
    return api.get<OpportunityListResult>(`/opportunities${suffix ? `?${suffix}` : ''}`)
  },
  getDetail: (id: string) => api.get<OpportunityDetail>(`/opportunities/${id}`),
  process: (id: string) => api.post<OpportunityDetail>(`/opportunities/${id}/process`),
  reprocess: (id: string) => api.post<OpportunityDetail>(`/opportunities/${id}/reprocess`),
  setLinks: (id: string, data: UpdateOpportunityLinksRequest) =>
    api.patch<OpportunityDetail>(`/opportunities/${id}/links`, data),
  setStatus: (id: string, status: OpportunityStatus) =>
    api.patch<OpportunityDetail>(`/opportunities/${id}/status`, { status }),
  remove: (id: string) => api.delete<void>(`/opportunities/${id}`),
}

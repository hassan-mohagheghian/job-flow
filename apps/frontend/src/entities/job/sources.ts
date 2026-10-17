import { api } from '@/shared/api'

export interface SourceStats {
  total_jobs: number
  total_sources: number
  active_sources: number
  unknown_jobs: number
}

export interface SourceDistributionItem {
  id: string
  name: string | null
  domain: string | null
  job_count: number
}

export interface SourceDistribution {
  items: SourceDistributionItem[]
  other_count: number
  unknown_count: number
}

export interface SourceListItem {
  id: string
  name: string | null
  canonical_url: string | null
  domain: string | null
  is_active: boolean
  job_count: number
  last_activity: string | null
}

export interface SourceListResponse {
  items: SourceListItem[]
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
  }
}

export interface SourceSortField {
  field: 'job_count' | 'name' | 'last_activity'
  order: 'asc' | 'desc'
}

export interface RecommendationItem {
  recommendation: 'apply' | 'consider' | 'skip' | 'none'
  count: number
}

export interface RecommendationDistribution {
  items: RecommendationItem[]
  total: number
}

export interface SourcesQuery extends SourceSortField {
  page: number
  page_size: number
  query: string
}

export const sourceApi = {
  stats: () => api.get<SourceStats>('/jobs/sources/stats'),
  distribution: (limit = 5) =>
    api.get<SourceDistribution>(`/jobs/sources/distribution?limit=${limit}`),
  recommendationDistribution: () =>
    api.get<RecommendationDistribution>('/jobs/recommendations/distribution'),
  sources: (query: SourcesQuery) => {
    const params = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
      sort: query.field,
      order: query.order,
    })
    if (query.query) params.set('query', query.query)
    return api.get<SourceListResponse>(`/jobs/sources?${params.toString()}`)
  },
}

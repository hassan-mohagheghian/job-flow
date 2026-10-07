'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { opportunityApi } from './api'
import type {
  CreateOpportunityRequest,
  OpportunityListQuery,
  OpportunityStatus,
  UpdateOpportunityLinksRequest,
} from './types'

export const OPPORTUNITIES_KEY = ['opportunities'] as const

export function opportunitiesListKey(query: OpportunityListQuery) {
  return [...OPPORTUNITIES_KEY, 'list', query.status ?? '', query.source ?? '', query.query ?? ''] as const
}

export function opportunityDetailKey(id: string) {
  return [...OPPORTUNITIES_KEY, 'detail', id] as const
}

export function useOpportunitiesQuery(query: OpportunityListQuery) {
  return useQuery({
    queryKey: opportunitiesListKey(query),
    queryFn: () => opportunityApi.list(query),
  })
}

export function useOpportunityDetailQuery(id: string | null) {
  return useQuery({
    queryKey: opportunityDetailKey(id ?? ''),
    queryFn: () => opportunityApi.getDetail(id as string),
    enabled: !!id,
  })
}

export function useCreateOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateOpportunityRequest) => opportunityApi.create(data),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: OPPORTUNITIES_KEY })
    },
  })
}

export function useProcessOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reprocess }: { id: string; reprocess?: boolean }) =>
      reprocess ? opportunityApi.reprocess(id) : opportunityApi.process(id),
    onSettled: (_data, _error, variables) => {
      qc.invalidateQueries({ queryKey: OPPORTUNITIES_KEY })
      if (variables?.id) {
        qc.invalidateQueries({ queryKey: opportunityDetailKey(variables.id) })
      }
    },
  })
}

export function useUpdateOpportunityLinks() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateOpportunityLinksRequest }) =>
      opportunityApi.setLinks(id, data),
    onSettled: (_data, _error, variables) => {
      qc.invalidateQueries({ queryKey: OPPORTUNITIES_KEY })
      if (variables?.id) {
        qc.invalidateQueries({ queryKey: opportunityDetailKey(variables.id) })
      }
    },
  })
}

export function useUpdateOpportunityStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: OpportunityStatus }) =>
      opportunityApi.setStatus(id, status),
    onSettled: (_data, _error, variables) => {
      qc.invalidateQueries({ queryKey: OPPORTUNITIES_KEY })
      if (variables?.id) {
        qc.invalidateQueries({ queryKey: opportunityDetailKey(variables.id) })
      }
    },
  })
}

export function useDeleteOpportunity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => opportunityApi.remove(id),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: OPPORTUNITIES_KEY })
    },
  })
}

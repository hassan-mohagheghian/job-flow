'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { applicationApi } from './api'
import type {
  ApplicationDocumentType,
  CreateFollowUpInput,
  CreateNoteInput,
  UpdateApplicationInput,
  UpdateFollowUpInput,
} from './types'

const APPLICATION_KEY = 'application'

/** Dashboard aggregate key, invalidated whenever applications are created or their status changes. */
export const applicationStatusDistributionKey = ['application-status-distribution'] as const

function applicationKeys(applicationId: string | null) {
  return [APPLICATION_KEY, applicationId ?? 'none'] as const
}

export function useApplicationQuery(applicationId: string | null) {
  return useQuery({
    queryKey: applicationKeys(applicationId),
    queryFn: () => applicationApi.get(applicationId!),
    enabled: !!applicationId,
  })
}

export function useApplicationByJobQuery(jobId: string | null) {
  return useQuery({
    queryKey: [APPLICATION_KEY, 'by-job', jobId],
    queryFn: () => applicationApi.getByJob(jobId!),
    enabled: !!jobId,
  })
}

export function useCreateApplicationMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, seenAt }: { jobId: string; seenAt?: string | null }) =>
      applicationApi.create(jobId, seenAt),
    onSuccess: (application) => {
      queryClient.setQueryData([APPLICATION_KEY, application.id], application)
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY, 'by-job'] })
      queryClient.invalidateQueries({ queryKey: applicationStatusDistributionKey })
    },
  })
}

export function useUpdateApplicationMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ applicationId, data }: { applicationId: string; data: UpdateApplicationInput }) =>
      applicationApi.update(applicationId, data),
    onSuccess: (application) => {
      queryClient.setQueryData([APPLICATION_KEY, application.id], application)
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY, 'by-job'] })
      queryClient.invalidateQueries({ queryKey: applicationStatusDistributionKey })
    },
  })
}

export function useUpdateTimelineMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ eventId, changedAt }: { eventId: string; changedAt: string | null }) =>
      applicationApi.updateTimeline(eventId, changedAt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useDeleteTimelineMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (eventId: string) => applicationApi.deleteTimeline(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useAddFollowUpMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ applicationId, input }: { applicationId: string; input: CreateFollowUpInput }) =>
      applicationApi.addFollowUp(applicationId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useUpdateFollowUpMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ followUpId, input }: { followUpId: string; input: UpdateFollowUpInput }) =>
      applicationApi.updateFollowUp(followUpId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useDeleteFollowUpMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (followUpId: string) => applicationApi.deleteFollowUp(followUpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useAddNoteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ applicationId, input }: { applicationId: string; input: CreateNoteInput }) =>
      applicationApi.addNote(applicationId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useDeleteNoteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (noteId: string) => applicationApi.deleteNote(noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useGenerateRoadmapMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (applicationId: string) => applicationApi.generateRoadmap(applicationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roadmap', 'by-application'] })
    },
  })
}

export function useGenerateDocumentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ applicationId, documentType }: { applicationId: string; documentType: ApplicationDocumentType }) =>
      applicationApi.generateDocument(applicationId, documentType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useUpdateDocumentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ documentId, content }: { documentId: string; content: string }) =>
      applicationApi.updateDocument(documentId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useDeleteDocumentMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => applicationApi.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [APPLICATION_KEY] })
    },
  })
}

export function useDownloadDocumentPdf() {
  return useMutation({
    mutationFn: ({ documentId, filename }: { documentId: string; filename: string }) =>
      applicationApi.downloadPdf(documentId, filename),
  })
}

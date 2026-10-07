'use client'

import { useState } from 'react'
import MainLayout from '@/widgets/main-layout'
import ConfirmDialog, { useConfirmDialog } from '@/shared/components/ConfirmDialog'
import { toast } from 'sonner'
import {
  useCreateOpportunity,
  useDeleteOpportunity,
  useOpportunitiesQuery,
} from '@/entities/opportunity/hooks'
import type { CreateOpportunityRequest, OpportunityStatus } from '@/entities/opportunity/types'
import { ApiError } from '@/shared/api/http-client'
import {
  OpportunitiesPage,
  OpportunityCreateDrawer,
  OpportunityDetailDrawer,
} from '@/features/opportunities'

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message || fallback
  if (error instanceof Error) return error.message || fallback
  return fallback
}

function OpportunitiesPageAdapter() {
  const [query, setQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<OpportunityStatus | ''>('')
  const [createOpen, setCreateOpen] = useState(false)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const { dialog: confirmDialog, showConfirm, onClose: closeConfirm } = useConfirmDialog()

  const listQuery = useOpportunitiesQuery({
    query: query.trim() || undefined,
    status: filterStatus || undefined,
    limit: 100,
  })
  const createMutation = useCreateOpportunity()
  const deleteMutation = useDeleteOpportunity()

  const handleCreate = (data: CreateOpportunityRequest) => {
    setCreateError(null)
    createMutation.mutate(data, {
      onSuccess: (detail) => {
        setCreateOpen(false)
        if (detail.duplicate) {
          toast.info('This message already exists — opened the existing opportunity')
          setDetailId(detail.id)
        } else {
          toast.success('Opportunity created')
        }
        setDetailId(detail.id)
      },
      onError: (error) => {
        setCreateError(extractErrorMessage(error, 'Failed to create opportunity'))
      },
    })
  }

  const handleDelete = async (id: string) => {
    const ok = await showConfirm(
      'Delete Opportunity',
      'Permanently delete this opportunity and its evaluation history?',
      'Delete',
    )
    if (!ok) return
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success('Opportunity deleted')
        setDetailId((current) => (current === id ? null : current))
      },
      onError: (error) => {
        toast.error(extractErrorMessage(error, 'Failed to delete opportunity'))
      },
    })
  }

  return (
    <div className="flex flex-col h-full">
      <OpportunitiesPage
        items={listQuery.data?.items ?? []}
        total={listQuery.data?.total ?? 0}
        isLoading={listQuery.isLoading}
        isError={listQuery.isError}
        onRefetch={() => listQuery.refetch()}
        query={query}
        onQueryChange={setQuery}
        filterStatus={filterStatus}
        onFilterStatusChange={setFilterStatus}
        onOpenCreate={() => {
          setCreateError(null)
          setCreateOpen(true)
        }}
        onOpenDetail={setDetailId}
        onDelete={handleDelete}
      />
      <OpportunityCreateDrawer
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={handleCreate}
        submitting={createMutation.isPending}
        error={createError}
      />
      <OpportunityDetailDrawer opportunityId={detailId} onClose={() => setDetailId(null)} />
      <ConfirmDialog dialog={confirmDialog} onClose={closeConfirm} />
    </div>
  )
}

export default function OpportunitiesPageWidget() {
  return (
    <MainLayout>
      <OpportunitiesPageAdapter />
    </MainLayout>
  )
}

'use client'

import dynamic from 'next/dynamic'
import MainLayout from '@/widgets/main-layout'
import { useState, useCallback, useMemo, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useJobsInfiniteQuery } from '@/features/jobs-v2/hooks/useJobsInfiniteQuery'
import { useAddJobShortcut } from '@/features/jobs-v2/hooks/useAddJobShortcut'
import { useAddJobPasteShortcut } from '@/features/jobs-v2/hooks/useAddJobPasteShortcut'
import { useProcessingEvents } from '@/shared/hooks/useProcessingEvents'
import { processingApi } from '@/entities/processing/api'
import ConfirmDialog, { useConfirmDialog } from '@/shared/components/ConfirmDialog'
import { toast } from 'sonner'
import { getSearchParam, setSearchParam } from '@/shared/lib/url'
import { readClipboardUrl } from '@/shared/lib/clipboard'
import { DropJobOverlay } from '@/features/jobs-v2/components/DropJobOverlay'

const JobsPageContent = dynamic(
  () => import('@/features/jobs-v2/components/JobsPage').then(m => ({ default: m.JobsPage })),
  { ssr: false }
)

function JobsPageV2Adapter() {
  const [queueDrawerOpen, setQueueDrawerOpen] = useState(false)
  const [queueReloadKey, setQueueReloadKey] = useState(0)
  const [addJobDrawerOpen, setAddJobDrawerOpen] = useState(false)
  const [addJobClipboardUrl, setAddJobClipboardUrl] = useState<string | null>(null)
  const [detailJobId, setDetailJobId] = useState<string | null>(null)
  const [editJobId, setEditJobId] = useState<string | null>(null)
  const [showRowNumberColumn, setShowRowNumberColumn] = useState(true)
  const { dialog: confirmDialog, showConfirm, onClose: closeConfirm } = useConfirmDialog()
  const router = useRouter()

  const {
    items, total, loadedCount, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage,
    isError, error, refetch, isRefetching,
    query, setQuery,
    sort, order, handleHeaderSort,
    filterProcessingStatus, setFilterProcessingStatus,
    filterLocation, setFilterLocation,
    filterRemote, setFilterRemote,
    filterVisa, setFilterVisa,
    filterPinned, setFilterPinned,
    filterRecommendation, setFilterRecommendation,
    filterTrackingStatus, setFilterTrackingStatus,
    filterCreatedDate, setFilterCreatedDate,
    activeFilterCount, clearFilters,
    processMutation,
    deleteMutation,
    pinnedMutation,
  } = useJobsInfiniteQuery()

  useProcessingEvents()

  const openAddJob = useCallback(async () => {
    const url = await readClipboardUrl()
    setAddJobClipboardUrl(url)
    setAddJobDrawerOpen(true)
  }, [])

  const openAddJobWithUrl = useCallback((url: string) => {
    setAddJobClipboardUrl(url)
    setAddJobDrawerOpen(true)
  }, [])

  useAddJobShortcut(openAddJob)
  useAddJobPasteShortcut(openAddJobWithUrl)

  const processingCount = useMemo(() => {
    return items.filter(i => {
      const s = i.latest_processing_execution?.status
      return s === 'queued' || s === 'running' || s === 'starting'
    }).length
  }, [items])

  const handleProcessV2 = useCallback((id: string) => {
    processMutation.mutate(id, {
      onSettled: () => setQueueReloadKey(k => k + 1),
    })
    setQueueDrawerOpen(true)
  }, [processMutation])

  const handleViewDetails = useCallback((id: string) => {
    setDetailJobId(id)
  }, [])

  const handleEdit = useCallback((id: string) => {
    setEditJobId(id)
  }, [])

  const handleDelete = useCallback(async (id: string) => {
    const ok = await showConfirm(
      'Delete Job',
      'Permanently delete this job and all its processing data?',
      'Delete',
    )
    if (!ok) return
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success('Job deleted')
        setDetailJobId((current) => (current === id ? null : current))
        setEditJobId((current) => (current === id ? null : current))
      },
      onError: () => {
        toast.error('Failed to delete job')
      },
    })
  }, [showConfirm, deleteMutation])

  const handleRetry = useCallback((id: string) => {
    processMutation.mutate(id, {
      onSettled: () => setQueueReloadKey(k => k + 1),
    })
    setQueueDrawerOpen(true)
  }, [processMutation])

  const handleCancel = useCallback((id: string) => {
    const job = items.find(j => j.id === id)
    const executionId = job?.latest_processing_execution?.id
    if (!executionId) return
    processingApi.cancel(executionId)
      .then(() => {
        toast.success('Cancelled processing')
        refetch()
      })
      .catch(() => toast.error('Failed to cancel processing'))
  }, [items, refetch])

  const handleTogglePinned = useCallback((id: string, pinned: boolean) => {
    pinnedMutation.mutate({ jobId: id, pinned })
  }, [pinnedMutation])

  const handleOpenApplication = useCallback((id: string) => {
    router.push(`/jobs/${id}/application`)
  }, [router])

  useEffect(() => {
    const jobId = getSearchParam('job')
    if (jobId) setDetailJobId(jobId)
  }, [])

  useEffect(() => {
    if (detailJobId === null) setSearchParam('job', null)
  }, [detailJobId])

  return (
    <DropJobOverlay onDropUrl={openAddJobWithUrl}>
      <div className="flex flex-col h-full">
        <JobsPageContent
          items={items}
          total={total}
          loadedCount={loadedCount}
          isLoading={isLoading}
          isFetchingNextPage={isFetchingNextPage}
          hasNextPage={hasNextPage}
          onFetchNextPage={fetchNextPage}
          isError={isError}
          error={error}
          onRefetch={refetch}
          isRefetching={isRefetching}
          query={query}
          onQueryChange={setQuery}
          sort={sort}
          onSortChange={handleHeaderSort}
          order={order}
          filterProcessingStatus={filterProcessingStatus}
          onFilterProcessingStatusChange={setFilterProcessingStatus}
          filterLocation={filterLocation}
          onFilterLocationChange={setFilterLocation}
          filterRemote={filterRemote}
          onFilterRemoteChange={setFilterRemote}
          filterVisa={filterVisa}
          onFilterVisaChange={setFilterVisa}
          filterPinned={filterPinned}
          onFilterPinnedChange={setFilterPinned}
          filterRecommendation={filterRecommendation}
          onFilterRecommendationChange={setFilterRecommendation}
          filterTrackingStatus={filterTrackingStatus}
          onFilterTrackingStatusChange={setFilterTrackingStatus}
          filterCreatedDate={filterCreatedDate}
          onFilterCreatedDateChange={setFilterCreatedDate}
          activeFilterCount={activeFilterCount}
          onClearFilters={clearFilters}
          onProcessV2={handleProcessV2}
          onReprocess={handleProcessV2}
          onViewDetails={handleViewDetails}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onTogglePinned={handleTogglePinned}
          onRetry={handleRetry}
          onCancel={handleCancel}
          onApplication={handleOpenApplication}
          showRowNumberColumn={showRowNumberColumn}
          onToggleRowNumberColumn={setShowRowNumberColumn}
          isProcessing={processMutation.isPending}
          queueDrawerOpen={queueDrawerOpen}
          onQueueDrawerOpenChange={setQueueDrawerOpen}
          queueReloadKey={queueReloadKey}
          addJobDrawerOpen={addJobDrawerOpen}
          onAddJobDrawerOpenChange={setAddJobDrawerOpen}
          onOpenAddJob={openAddJob}
          onAddJobUrl={openAddJobWithUrl}
          addJobClipboardUrl={addJobClipboardUrl}
          onJobQueued={() => setQueueReloadKey(k => k + 1)}
          detailJobId={detailJobId}
          onDetailJobIdChange={setDetailJobId}
          editJobId={editJobId}
          onEditJobIdChange={setEditJobId}
          processingCount={processingCount}
        />
        <ConfirmDialog dialog={confirmDialog} onClose={closeConfirm} />
      </div>
    </DropJobOverlay>
  )
}

export default function JobsPageV2Widget() {
  return (
    <MainLayout>
      <JobsPageV2Adapter />
    </MainLayout>
  )
}

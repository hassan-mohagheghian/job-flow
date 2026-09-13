'use client'

import { useCallback } from 'react'
import type { JobListItem, ProcessingStatusFilter, RecommendationFilter, TrackingStatusFilter, CreatedDateFilter } from '@/entities/job/types'
import { Button } from '@/shared/ui/button'
import { JobsHeader } from './JobsHeader'
import { JobsToolbar } from './JobsToolbar'
import { JobsTable } from './JobsTable'
import { ProcessingDrawer } from './ProcessingDrawer'
import { JobDetailDrawer } from './JobDetailDrawer'
import { JobEditDrawer } from './JobEditDrawer'
import CreateEntityDrawer, { type CreateEntityFormData } from '@/shared/components/CreateEntityDrawer'
import { useCreateJob } from '@/features/jobs-v2/hooks/useCreateJob'
import { useJobTimeline } from '@/features/jobs-v2/hooks/useJobTimeline'
import { JobTimeline } from './JobTimeline'
import { toast } from 'sonner'

interface JobsPageProps {
  items: JobListItem[]
  total: number
  loadedCount: number
  isLoading: boolean
  isFetchingNextPage: boolean
  hasNextPage: boolean
  onFetchNextPage: () => void
  isError: boolean
  error: Error | null
  onRefetch: () => void
  isRefetching?: boolean
  query: string
  onQueryChange: (value: string) => void
  sort: string
  onSortChange: (value: string) => void
  order: 'asc' | 'desc'
  filterProcessingStatus: ProcessingStatusFilter
  onFilterProcessingStatusChange: (value: ProcessingStatusFilter) => void
  filterLocation: string
  onFilterLocationChange: (value: string) => void
  filterRemote: boolean | ''
  onFilterRemoteChange: (value: boolean | '') => void
  filterVisa: boolean | ''
  onFilterVisaChange: (value: boolean | '') => void
  filterPinned: boolean
  onFilterPinnedChange: (value: boolean) => void
  filterRecommendation: RecommendationFilter[]
  onFilterRecommendationChange: (value: RecommendationFilter[]) => void
  filterTrackingStatus: TrackingStatusFilter[]
  onFilterTrackingStatusChange: (value: TrackingStatusFilter[]) => void
  filterCreatedDate: CreatedDateFilter
  onFilterCreatedDateChange: (value: CreatedDateFilter) => void
  activeFilterCount: number
  onClearFilters: () => void
  onProcessV2: (id: string) => void
  onReprocess: (id: string) => void
  onViewDetails: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTogglePinned: (id: string) => void
  onRetry?: (id: string) => void
  onCancel?: (id: string) => void
  onApplication?: (id: string) => void
  showPinnedColumn?: boolean
  onTogglePinnedColumn?: (value: boolean) => void
  showRowNumberColumn?: boolean
  onToggleRowNumberColumn?: (value: boolean) => void
  isProcessing: boolean
  queueDrawerOpen: boolean
  onQueueDrawerOpenChange: (open: boolean) => void
  queueReloadKey?: number
  addJobDrawerOpen: boolean
  onAddJobDrawerOpenChange: (open: boolean) => void
  onOpenAddJob: () => void
  onAddJobUrl: (url: string) => void
  addJobClipboardUrl: string | null
  onJobQueued?: () => void
  detailJobId: string | null
  onDetailJobIdChange: (id: string | null) => void
  editJobId: string | null
  onEditJobIdChange: (id: string | null) => void
  processingCount: number
}

export function JobsPage({
  items, total, loadedCount, isLoading, isFetchingNextPage, hasNextPage, onFetchNextPage,
  isError, error, onRefetch, isRefetching,
  query, onQueryChange,
  sort, onSortChange, order,
  filterProcessingStatus, onFilterProcessingStatusChange,
  filterLocation, onFilterLocationChange,
  filterRemote, onFilterRemoteChange,
  filterVisa, onFilterVisaChange,
  filterPinned, onFilterPinnedChange,
  filterRecommendation, onFilterRecommendationChange,
  filterTrackingStatus, onFilterTrackingStatusChange,
  filterCreatedDate, onFilterCreatedDateChange,
  activeFilterCount, onClearFilters,
  onProcessV2, onReprocess, onViewDetails, onEdit, onDelete, onTogglePinned, onRetry, onCancel, onApplication, isProcessing,
  showPinnedColumn = true, onTogglePinnedColumn,
  showRowNumberColumn = false, onToggleRowNumberColumn,
  queueDrawerOpen, onQueueDrawerOpenChange, queueReloadKey,
  addJobDrawerOpen, onAddJobDrawerOpenChange, onOpenAddJob, onAddJobUrl, addJobClipboardUrl, onJobQueued,
  detailJobId, onDetailJobIdChange,
  editJobId, onEditJobIdChange,
  processingCount,
}: JobsPageProps) {
  const { createJob, submitting, error: createError, existingJobId, existingJob, clearError } = useCreateJob()
  const timeline = useJobTimeline()

  const handleCreateJob = useCallback(async (data: CreateEntityFormData) => {
    const result = await createJob({
      job_post_url: data.job_post_url ?? '',
      job_title: data.job_title,
      links: data.links,
      notes: data.notes.map((n) => ({ title: n.title || '', content: n.content })),
      queue: data.queue,
    })
    if (result) {
      toast.success(data.queue ? 'Job created and queued' : 'Job created successfully')
      onAddJobDrawerOpenChange(false)
      onRefetch()
      if (data.queue) {
        onJobQueued?.()
        onQueueDrawerOpenChange(true)
      }
    }
  }, [createJob, onAddJobDrawerOpenChange, onRefetch, onJobQueued, onQueueDrawerOpenChange])

  if (isError) {
    return (
      <div className="flex flex-col h-full rounded-lg border overflow-hidden bg-card">
        <JobsHeader
          total={total}
          loadedCount={loadedCount}
          processingCount={processingCount}
          onOpenQueue={() => onQueueDrawerOpenChange(true)}
          onAddJob={onOpenAddJob}
          onAddJobUrl={onAddJobUrl}
          onRefresh={onRefetch}
          isRefreshing={isRefetching}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <p className="text-sm text-red-500">Unable to load jobs</p>
            <p className="text-xs text-muted-foreground">{error?.message || 'An unexpected error occurred'}</p>
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onRefetch}>
              Retry
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full rounded-lg border overflow-hidden bg-card">
      <JobsHeader
        total={total}
        loadedCount={loadedCount}
        processingCount={processingCount}
        onOpenQueue={() => onQueueDrawerOpenChange(true)}
        onAddJob={onOpenAddJob}
        onAddJobUrl={onAddJobUrl}
        onRefresh={onRefetch}
        isRefreshing={isRefetching}
      />
      <div className="flex flex-1 min-h-0">
        <div className="flex flex-col flex-1 min-w-0 min-h-0">
          <JobsToolbar
            query={query}
            onQueryChange={onQueryChange}
            filterProcessingStatus={filterProcessingStatus}
            onFilterProcessingStatusChange={onFilterProcessingStatusChange}
            filterLocation={filterLocation}
            onFilterLocationChange={onFilterLocationChange}
            filterRemote={filterRemote}
            onFilterRemoteChange={onFilterRemoteChange}
            filterVisa={filterVisa}
            onFilterVisaChange={onFilterVisaChange}
            filterPinned={filterPinned}
            onFilterPinnedChange={onFilterPinnedChange}
            filterRecommendation={filterRecommendation}
            onFilterRecommendationChange={onFilterRecommendationChange}
            filterTrackingStatus={filterTrackingStatus}
            onFilterTrackingStatusChange={onFilterTrackingStatusChange}
            filterCreatedDate={filterCreatedDate}
            onFilterCreatedDateChange={onFilterCreatedDateChange}
            activeFilterCount={activeFilterCount}
            onClearFilters={onClearFilters}
            showPinnedColumn={showPinnedColumn}
            onTogglePinnedColumn={onTogglePinnedColumn}
            showRowNumberColumn={showRowNumberColumn}
            onToggleRowNumberColumn={onToggleRowNumberColumn}
          />
          <JobsTable
            items={items}
            total={total}
            loadedCount={loadedCount}
            isLoading={isLoading}
            isFetchingNextPage={isFetchingNextPage}
            hasNextPage={hasNextPage}
            onFetchNextPage={onFetchNextPage}
            onProcessV2={onProcessV2}
            onViewDetails={onViewDetails}
            onEdit={onEdit}
            onDelete={onDelete}
            onTogglePinned={onTogglePinned}
            onRetry={onRetry}
            onCancel={onCancel}
            onApplication={onApplication}
            showPinnedColumn={showPinnedColumn}
            showRowNumberColumn={showRowNumberColumn}
            sort={sort}
            order={order}
            onSortChange={onSortChange}
          />
        </div>
        <JobTimeline days={timeline.data?.days ?? []} isLoading={timeline.isLoading} />
      </div>
      <ProcessingDrawer
        open={queueDrawerOpen}
        onOpenChange={onQueueDrawerOpenChange}
        reloadKey={queueReloadKey}
      />
      <JobDetailDrawer
        jobId={detailJobId}
        onOpenChange={onDetailJobIdChange}
        onEdit={onEdit}
        onReprocess={onReprocess}
      />
      <JobEditDrawer
        jobId={editJobId}
        onOpenChange={onEditJobIdChange}
      />
      <CreateEntityDrawer
        mode="job"
        open={addJobDrawerOpen}
        onOpenChange={(open) => { onAddJobDrawerOpenChange(open); if (!open) clearError() }}
        onSubmit={handleCreateJob}
        submitting={submitting}
        error={createError}
        clipboardUrl={addJobClipboardUrl}
        existingJob={existingJob}
        onViewJobDetails={(id) => onDetailJobIdChange(id)}
        errorLink={existingJobId ? { label: 'Open application', href: `/jobs/${encodeURIComponent(existingJobId)}/application` } : null}
      />
    </div>
  )
}

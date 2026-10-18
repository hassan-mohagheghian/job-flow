'use client'

import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/shared/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import type { ApplicationStatus } from '@/entities/application/types'
import {
  useApplicationByJobQuery,
  useCreateApplicationMutation,
  useUpdateApplicationMutation,
} from '@/entities/application/hooks'
import { STATUS_OPTIONS } from '@/features/job-application/components/ApplicationTracker'

interface TrackingStatusSelectProps {
  jobId: string
  /**
   * What to render when the job has no application yet:
   * - 'button' (default): an inline "Mark expired" button that creates the
   *   application and sets it to expired in one step.
   * - 'placeholder': a disabled select showing "Not applied", for callers that
   *   render their own action buttons (the Job Detail drawer stacks
   *   Mark applied / Mark expired / Mark as dismissed next to this select).
   */
  emptyMode?: 'button' | 'placeholder'
}

function invalidateJobCaches(queryClient: ReturnType<typeof useQueryClient>, jobId: string) {
  queryClient.invalidateQueries({ queryKey: ['jobs-v2-infinite'] })
  queryClient.invalidateQueries({ queryKey: ['job-detail', jobId] })
}

export function TrackingStatusSelect({ jobId, emptyMode = 'button' }: TrackingStatusSelectProps) {
  const queryClient = useQueryClient()
  const { data: application, isLoading, isError } = useApplicationByJobQuery(jobId)
  const updateApplication = useUpdateApplicationMutation()
  const createApplication = useCreateApplicationMutation()

  const handleStatusChange = (status: ApplicationStatus) => {
    if (!application) return
    updateApplication.mutate(
      { applicationId: application.id, data: { status } },
      { onSuccess: () => invalidateJobCaches(queryClient, jobId) },
    )
  }

  const handleMarkExpired = () => {
    createApplication.mutate(
      { jobId },
      {
        onSuccess: (created) => {
          updateApplication.mutate(
            { applicationId: created.id, data: { status: 'expired' } },
            { onSuccess: () => invalidateJobCaches(queryClient, jobId) },
          )
        },
      },
    )
  }

  if (isLoading) {
    return <span className="text-2xs text-muted-foreground">Loading…</span>
  }

  if (isError || !application) {
    if (emptyMode === 'placeholder') {
      return (
        <Select value="" disabled>
          <SelectTrigger size="sm" className="w-full justify-between capitalize" aria-label="Tracking status">
            <SelectValue placeholder="Not applied" />
          </SelectTrigger>
        </Select>
      )
    }
    return (
      <Button
        size="sm"
        variant="outline"
        onClick={handleMarkExpired}
        disabled={createApplication.isPending || updateApplication.isPending}
      >
        {createApplication.isPending || updateApplication.isPending ? 'Marking…' : 'Mark expired'}
      </Button>
    )
  }

  return (
    <Select
      value={application.status}
      onValueChange={handleStatusChange}
      disabled={updateApplication.isPending}
    >
      <SelectTrigger size="sm" className="w-full justify-between capitalize" aria-label="Tracking status">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {STATUS_OPTIONS.map((status) => (
          <SelectItem key={status} value={status} className="capitalize">
            {status.replace(/_/g, ' ')}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

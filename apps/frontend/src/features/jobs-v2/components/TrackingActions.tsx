'use client'

import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/shared/ui/button'
import {
  useApplicationByJobQuery,
  useCreateApplicationMutation,
  useUpdateApplicationMutation,
} from '@/entities/application/hooks'
import type { ApplicationStatus } from '@/entities/application/types'

interface TrackingActionsProps {
  jobId: string
  className?: string
  /**
   * Subset of quick actions to render. Defaults to every action, preserving the
   * declaration order below. The Job Detail drawer splits them across two
   * columns: `applied` next to the status select and `expired` in the Actions
   * group after Work Types.
   */
  statuses?: ReadonlyArray<ApplicationStatus>
}

/**
 * Quick actions that push a job's application straight to a funnel status.
 *
 * They work with or without an existing application: when the job has none,
 * one is created first and then patched to the target status (the same
 * two-step the legacy inline "Mark expired" button used).
 *
 * Rendered as full-width buttons so the caller controls the layout. The Job
 * Detail drawer renders `applied` next to the status select and `expired` in
 * the second column's Actions group.
 */
const QUICK_ACTIONS: ReadonlyArray<{ status: ApplicationStatus; label: string }> = [
  { status: 'applied', label: 'Mark applied' },
  { status: 'expired', label: 'Mark expired' },
]

export function TrackingActions({ jobId, className, statuses }: TrackingActionsProps) {
  const queryClient = useQueryClient()
  const { data: application } = useApplicationByJobQuery(jobId)
  const createApplication = useCreateApplicationMutation()
  const updateApplication = useUpdateApplicationMutation()

  const pending = createApplication.isPending || updateApplication.isPending

  const invalidateJobCaches = () => {
    queryClient.invalidateQueries({ queryKey: ['jobs-v2-infinite'] })
    queryClient.invalidateQueries({ queryKey: ['job-detail', jobId] })
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
  }

  const handleSetStatus = (status: ApplicationStatus) => {
    if (application) {
      updateApplication.mutate(
        { applicationId: application.id, data: { status } },
        { onSuccess: invalidateJobCaches },
      )
      return
    }
    createApplication.mutate(
      { jobId },
      {
        onSuccess: (created) => {
          updateApplication.mutate(
            { applicationId: created.id, data: { status } },
            { onSuccess: invalidateJobCaches },
          )
        },
      },
    )
  }

  const actions = statuses
    ? QUICK_ACTIONS.filter(({ status }) => statuses.includes(status))
    : QUICK_ACTIONS

  return (
    <>
      {actions.map(({ status, label }) => (
        <Button
          key={status}
          size="sm"
          variant="outline"
          className={className}
          disabled={pending}
          onClick={() => handleSetStatus(status)}
        >
          {pending ? 'Saving…' : label}
        </Button>
      ))}
    </>
  )
}

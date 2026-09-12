'use client'

import { useState } from 'react'
import { Check, Plus, Trash, NotePencil } from '@phosphor-icons/react'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import DateTime from '@/shared/components/DateTime'
import { toDatetimeLocalInput, toIsoFromLocalInput } from '@/shared/lib/datetimeInput'
import type { ApplicationDetail, ApplicationFollowUp, ApplicationStatus, ApplicationStatusEvent } from '@/entities/application/types'
import { useUpdateApplicationMutation, useAddFollowUpMutation, useUpdateFollowUpMutation, useDeleteFollowUpMutation, useUpdateTimelineMutation, useDeleteTimelineMutation } from '@/entities/application/hooks'
import { ApplicationStatusBadge } from './ApplicationStatusBadge'

interface ApplicationTrackerProps {
  application: ApplicationDetail
}

export const STATUS_OPTIONS: ApplicationStatus[] = [
  'preparing',
  'ready_to_apply',
  'applied',
  'interview',
  'offer',
  'accepted',
  'rejected',
  'withdrawn',
  'expired',
]

export function ApplicationTracker({ application }: ApplicationTrackerProps) {
  const updateApplication = useUpdateApplicationMutation()
  const addFollowUp = useAddFollowUpMutation()
  const updateFollowUp = useUpdateFollowUpMutation()
  const deleteFollowUp = useDeleteFollowUpMutation()
  const updateTimeline = useUpdateTimelineMutation()
  const deleteTimeline = useDeleteTimelineMutation()

  const [note, setNote] = useState('')
  const [scheduledAt, setScheduledAt] = useState('')

  const handleStatusChange = (status: ApplicationStatus) => {
    updateApplication.mutate({ applicationId: application.id, data: { status } })
  }

  const handleTimelineChange = (event: ApplicationStatusEvent, value: string) => {
    const changedAt = toIsoFromLocalInput(value)
    if (changedAt === null) return
    updateTimeline.mutate({ eventId: event.id, changedAt })
  }

  const handleAddFollowUp = () => {
    addFollowUp.mutate({
      applicationId: application.id,
      input: {
        note,
        scheduled_at: scheduledAt || null,
      },
    })
    setNote('')
    setScheduledAt('')
  }

  const handleToggleFollowUp = (followUp: ApplicationFollowUp) => {
    updateFollowUp.mutate({ followUpId: followUp.id, input: { completed: !followUp.completed_at } })
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="application-status" className="text-2xs font-medium text-muted-foreground uppercase tracking-wide">
          Status
        </label>
        <Select value={application.status} onValueChange={handleStatusChange}>
          <SelectTrigger id="application-status" size="sm" className="w-full justify-between">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((status) => (
              <SelectItem key={status} value={status}>
                {status.replace(/_/g, ' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="border-t border-border/40 pt-3 space-y-2">
        <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide">
          Application Timeline
        </p>
        {application.status_timeline.length === 0 && (
          <p className="text-xs text-muted-foreground">No status changes recorded yet.</p>
        )}
        <ul className="space-y-1.5">
          {application.status_timeline.map((event) => (
            <li key={event.id} className="flex items-center gap-2 group">
              <ApplicationStatusBadge status={event.status} className="w-28 justify-center shrink-0" />
              <Input
                type="datetime-local"
                aria-label={`${event.status.replace(/_/g, ' ')} changed at`}
                value={toDatetimeLocalInput(event.changed_at)}
                onChange={(e) => handleTimelineChange(event, e.target.value)}
                className="h-7 text-xs flex-1"
              />
              {event.status !== 'seen' && (
                <button
                  type="button"
                  aria-label={`Delete ${event.status.replace(/_/g, ' ')} timeline entry`}
                  onClick={() => deleteTimeline.mutate(event.id)}
                  className="text-muted-foreground/50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash className="w-3.5 h-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
        <p className="text-2xs text-muted-foreground">
          'Seen' is the mandatory starting point. Selecting a new status records its time
          automatically; edit or remove entries here (the last entry sets the status).
        </p>
      </div>

      <div className="border-t border-border/40 pt-3 space-y-2">
        <p className="text-2xs font-medium text-muted-foreground uppercase tracking-wide">
          Follow-ups
        </p>
        {application.follow_ups.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No follow-ups scheduled yet.
          </p>
        )}
        <ul className="space-y-1.5">
          {application.follow_ups.map((followUp) => (
            <li key={followUp.id} className="flex items-center gap-2 group">
              <button
                type="button"
                aria-label={followUp.completed_at ? 'Mark not done' : 'Mark done'}
                onClick={() => handleToggleFollowUp(followUp)}
                className={`inline-flex items-center justify-center w-4 h-4 shrink-0 rounded border transition-colors ${
                  followUp.completed_at
                    ? 'bg-green-500 border-green-500 text-white'
                    : 'border-border text-transparent hover:border-emerald-500'
                }`}
              >
                <Check className="w-3 h-3" />
              </button>
              <div className="flex-1 min-w-0 flex flex-wrap items-baseline gap-x-2">
                <span className={`text-xs ${followUp.completed_at ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                  {followUp.note || 'Follow-up'}
                </span>
                {followUp.scheduled_at && (
                  <span className="text-2xs text-muted-foreground">
                    <DateTime value={followUp.scheduled_at} />
                  </span>
                )}
              </div>
              <button
                type="button"
                aria-label="Delete follow-up"
                onClick={() => deleteFollowUp.mutate(followUp.id)}
                className="text-muted-foreground/50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>

        <div className="flex flex-col sm:flex-row gap-2 pt-1">
          <Input
            placeholder="Note (e.g. follow up after interview)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="h-7 text-xs flex-1"
          />
          <Input
            id="follow-up-scheduled-at"
            type="date"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="h-7 text-xs w-40"
          />
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={handleAddFollowUp}
            disabled={!note.trim() && !scheduledAt}
          >
            {addFollowUp.isPending ? (
              <NotePencil className="w-3.5 h-3.5 animate-pulse" />
            ) : (
              <Plus className="w-3.5 h-3.5" />
            )}
            Add
          </Button>
        </div>
      </div>
    </div>
  )
}

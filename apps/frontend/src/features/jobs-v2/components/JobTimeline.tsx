'use client'

import { useMemo } from 'react'
import type { JobTimelineDay } from '@/entities/job/types'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

interface JobTimelineProps {
  days: JobTimelineDay[]
  isLoading?: boolean
}

function monthKey(date: string): string {
  return date.slice(0, 7) // "YYYY-MM"
}

function formatMonth(date: string): string {
  const [y, m] = date.slice(0, 7).split('-').map(Number)
  const month = new Date(Date.UTC(y, m - 1, 1)).toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  return `${month} ${y}`
}

function formatDay(date: string): string {
  const [y, m, d] = date.split('-').map(Number)
  const day = new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
  return day
}

export function JobTimeline({ days, isLoading = false }: JobTimelineProps) {
  const groups = useMemo(() => {
    const result: { month: string; items: JobTimelineDay[] }[] = []
    for (const day of days) {
      const mk = monthKey(day.date)
      const last = result[result.length - 1]
      if (!last || last.month !== mk) result.push({ month: mk, items: [day] })
      else last.items.push(day)
    }
    return result
  }, [days])

  return (
    <aside className="w-24 shrink-0 border-l border-border/40 bg-card/40 flex flex-col">
      <header className="px-2 py-2 border-b border-border/40">
        <p className="text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
          Jobs added
        </p>
      </header>
      <div className="flex-1 overflow-y-auto py-1">
        {isLoading ? (
          <p className="text-2xs text-muted-foreground px-2 py-2">Loading…</p>
        ) : groups.length === 0 ? (
          <p className="text-2xs text-muted-foreground px-2 py-2">No jobs yet</p>
        ) : (
          groups.map((group) => (
            <div key={group.month}>
              <div className="flex items-center gap-1 px-1 mt-2 mb-0.5">
                <span className="h-px flex-1 bg-border/60" />
                <span className="text-2xs font-medium text-foreground/70 whitespace-nowrap">
                  {formatMonth(group.items[0].date)}
                </span>
                <span className="h-px flex-1 bg-border/60" />
              </div>
              {group.items.map((day) => {
                const apply = day.apply_count ?? 0
                return (
                  <Tooltip key={day.date}>
                    <TooltipTrigger asChild>
                      <div className="flex items-center justify-between gap-1 px-2 py-1 cursor-default">
                        <span className="text-xs text-foreground">{formatDay(day.date)}</span>
                        <span className="flex flex-col items-end leading-tight">
                          <span className="text-xs font-semibold tabular-nums text-primary">
                            {day.count}
                          </span>
                          {apply > 0 && (
                            <span className="text-2xs tabular-nums text-muted-foreground">
                              ({apply} apply)
                            </span>
                          )}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="left" className="max-w-56">
                      {apply > 0
                        ? `${apply} of ${day.count} jobs added ${formatDay(day.date)} have been applied to.`
                        : `Nothing applied from ${formatDay(day.date)} yet.`}
                    </TooltipContent>
                  </Tooltip>
                )
              })}
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useMemo } from 'react'
import type {
  ApplicationStatus,
  ApplicationStatusDistribution,
} from '@/entities/application/types'

interface ImportantStatus {
  status: ApplicationStatus
  label: string
  color: string
}

const IMPORTANT_STATUSES: ImportantStatus[] = [
  { status: 'applied', label: 'Applied', color: 'hsl(143 85% 39%)' },
  { status: 'interview', label: 'Interview', color: 'hsl(189 94% 43%)' },
  { status: 'offer', label: 'Offer', color: 'hsl(271 81% 56%)' },
  { status: 'accepted', label: 'Accepted', color: 'hsl(160 84% 39%)' },
  { status: 'rejected', label: 'Rejected', color: 'hsl(0 84% 60%)' },
]

/** Statuses that precede the first application submission. */
const PRE_APPLICATION_STATUSES: ApplicationStatus[] = [
  'seen',
  'preparing',
  'ready_to_apply',
]

const NOT_APPLIED_COLOR = 'hsl(38 92% 50%)'
const OTHER_COLOR = 'hsl(0 0% 55%)'

export interface ApplicationStatusSlice {
  key: string
  label: string
  job_count: number
  color: string
}

/**
 * Dashboard doughnut data: an amber "Not applied" slice for every
 * pre-application status, the five important outcomes in fixed order, plus a
 * single gray bucket for every remaining status. Percentages use all
 * applications as the denominator.
 */
export function buildApplicationStatusSlices(
  distribution: ApplicationStatusDistribution,
): {
  slices: ApplicationStatusSlice[]
  total: number
  pct: (count: number) => string
} {
  const byStatus = new Map(
    distribution.items.map((item) => [item.status, item.count]),
  )
  const itemsTotal = distribution.items.reduce((acc, item) => acc + item.count, 0)
  const total = Math.max(distribution.total || 0, itemsTotal)
  const pct = (count: number) => (total > 0 ? `${Math.round((count / total) * 100)}%` : '0%')

  const slices: ApplicationStatusSlice[] = []

  const notAppliedCount = PRE_APPLICATION_STATUSES.reduce(
    (acc, status) => acc + (byStatus.get(status) ?? 0),
    0,
  )
  if (notAppliedCount > 0) {
    slices.push({
      key: 'not_applied',
      label: 'Not applied',
      job_count: notAppliedCount,
      color: NOT_APPLIED_COLOR,
    })
  }

  slices.push(
    ...IMPORTANT_STATUSES.map(({ status, label, color }) => ({
      key: status,
      label,
      job_count: byStatus.get(status) ?? 0,
      color,
    })).filter((slice) => slice.job_count > 0),
  )

  const bucketedTotal = slices.reduce((acc, slice) => acc + slice.job_count, 0)
  const otherCount = Math.max(total - bucketedTotal, 0)
  if (otherCount > 0) {
    slices.push({
      key: 'other',
      label: 'Other statuses',
      job_count: otherCount,
      color: OTHER_COLOR,
    })
  }

  return { slices, total, pct }
}

interface ApplicationStatusChartProps {
  distribution: ApplicationStatusDistribution | undefined
  isLoading?: boolean
}

export function ApplicationStatusChart({
  distribution,
  isLoading = false,
}: ApplicationStatusChartProps) {
  const { slices, total, pct } = useMemo(
    () => buildApplicationStatusSlices(distribution ?? { items: [], total: 0 }),
    [distribution],
  )

  if (isLoading) return <div className="h-64 animate-pulse rounded bg-muted" />

  if (!distribution || slices.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No applications yet — track a job to populate this chart.
      </div>
    )
  }

  return (
    <div
      data-testid="application-status-chart"
      aria-label="Applications by status chart"
    >
      <div
        className="h-56"
        role="img"
        aria-label="Doughnut chart of applications per status"
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="job_count"
              nameKey="label"
              innerRadius="58%"
              outerRadius="88%"
              paddingAngle={2}
              strokeWidth={0}
            >
              {slices.map((slice) => (
                <Cell key={slice.key} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name) => [`${value} (${pct(value)})`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <dl className="mt-3 space-y-1 text-sm">
        {slices.map((slice) => (
          <div key={slice.key} className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-2 truncate">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: slice.color }}
                aria-hidden
              />
              <span className="truncate">{slice.label}</span>
            </dt>
            <dd className="tabular-nums text-muted-foreground">
              {slice.job_count} • {pct(slice.job_count)}
            </dd>
          </div>
        ))}
        <div className="pt-1 text-xs text-muted-foreground">
          {total.toLocaleString()} total applications
        </div>
      </dl>
    </div>
  )
}

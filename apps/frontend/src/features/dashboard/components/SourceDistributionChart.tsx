'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useMemo } from 'react'
import type { SourceDistribution, SourceDistributionItem } from '@/entities/job/sources'

const TOP_COLORS = [
  'hsl(221 83% 53%)',
  'hsl(173 80% 40%)',
  'hsl(271 81% 56%)',
  'hsl(12 76% 61%)',
  'hsl(42 88% 45%)',
]
const OTHER_COLOR = 'hsl(0 0% 55%)'
const UNKNOWN_COLOR = 'hsl(0 0% 35%)'

export interface ChartSlice {
  key: string
  label: string
  job_count: number
  color: string
}

/** Top 5 sources + Other + Unknown, with percentages against total listings. */
export function buildSlices(distribution: SourceDistribution): {
  slices: ChartSlice[]
  total: number
  pct: (count: number) => string
} {
  const total =
    distribution.items.reduce((acc, item) => acc + item.job_count, 0) +
    distribution.other_count +
    distribution.unknown_count
  const pct = (count: number) => (total > 0 ? `${Math.round((count / total) * 100)}%` : '0%')

  const slices: ChartSlice[] = distribution.items.map(
    (item: SourceDistributionItem, index: number) => ({
      key: item.id,
      label: item.name || item.domain || 'Unknown source',
      job_count: item.job_count,
      color: TOP_COLORS[index % TOP_COLORS.length],
    }),
  )
  if (distribution.other_count > 0) {
    slices.push({
      key: 'other',
      label: 'Other',
      job_count: distribution.other_count,
      color: OTHER_COLOR,
    })
  }
  if (distribution.unknown_count > 0) {
    slices.push({
      key: 'unknown',
      label: 'Unknown',
      job_count: distribution.unknown_count,
      color: UNKNOWN_COLOR,
    })
  }
  return { slices, total, pct }
}

interface SourceDistributionChartProps {
  distribution: SourceDistribution | undefined
  isLoading?: boolean
}

export function SourceDistributionChart({
  distribution,
  isLoading = false,
}: SourceDistributionChartProps) {
  const { slices, total, pct } = useMemo(
    () => buildSlices(distribution ?? { items: [], other_count: 0, unknown_count: 0 }),
    [distribution],
  )

  if (isLoading) return <div className="h-64 animate-pulse rounded bg-muted" />

  if (!distribution || slices.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No sources yet — import jobs to populate the dashboard.
      </div>
    )
  }

  return (
    <div data-testid="source-distribution-chart" aria-label="Listings by source chart">
      <div className="h-56" role="img" aria-label="Doughnut chart of listings per source">
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
          {total.toLocaleString()} total listings
        </div>
      </dl>
    </div>
  )
}

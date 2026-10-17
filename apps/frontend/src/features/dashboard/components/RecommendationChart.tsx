'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useMemo } from 'react'
import type { RecommendationDistribution } from '@/entities/job/sources'

const REC_COLORS: Record<string, string> = {
  apply: 'hsl(143 85% 39%)',
  consider: 'hsl(42 88% 45%)',
  skip: 'hsl(0 84% 60%)',
  none: 'hsl(0 0% 63%)',
}

const REC_LABELS: Record<string, string> = {
  apply: 'Apply',
  consider: 'Consider',
  skip: 'Skip',
  none: 'No analysis',
}

export interface RecommendationSlice {
  key: string
  label: string
  job_count: number
  color: string
}

/** Dashboard pie data: all four recommendation buckets, zero count = hidden. */
export function buildRecommendationSlices(distribution: RecommendationDistribution): {
  slices: RecommendationSlice[]
  total: number
  pct: (count: number) => string
} {
  const keys = ['apply', 'consider', 'skip', 'none'] as const
  const byRec = new Map(
    distribution.items.map((item) => [item.recommendation, item.count]),
  )
  const total = distribution.items.reduce((acc, item) => acc + item.count, 0)
  const pct = (count: number) => (total > 0 ? `${Math.round((count / total) * 100)}%` : '0%')
  const slices = keys
    .map((key) => ({
      key,
      label: REC_LABELS[key],
      job_count: byRec.get(key) ?? 0,
      color: REC_COLORS[key],
    }))
    .filter((slice) => slice.job_count > 0)
  return { slices, total, pct }
}

interface RecommendationChartProps {
  distribution: RecommendationDistribution | undefined
  isLoading?: boolean
}

export function RecommendationChart({
  distribution,
  isLoading = false,
}: RecommendationChartProps) {
  const { slices, total, pct } = useMemo(
    () => buildRecommendationSlices(distribution ?? { items: [], total: 0 }),
    [distribution],
  )

  if (isLoading) return <div className="h-64 animate-pulse rounded bg-muted" />

  if (!distribution || slices.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No recommendations yet — process jobs to populate this chart.
      </div>
    )
  }

  return (
    <div
      data-testid="recommendation-chart"
      aria-label="Jobs by recommendation chart"
    >
      <div className="h-56" role="img" aria-label="Doughnut chart of jobs per recommendation">
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

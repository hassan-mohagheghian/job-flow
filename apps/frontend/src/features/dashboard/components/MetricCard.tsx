'use client'

interface MetricCardProps {
  label: string
  value: number
  accent?: 'default' | 'warning'
}

export function MetricCard({ label, value, accent = 'default' }: MetricCardProps) {
  return (
    <div
      data-testid="metric-card"
      className="rounded-lg border bg-card p-4 shadow-sm"
      aria-label={`${label}: ${value}`}
    >
      <div className="text-2xl font-semibold tabular-nums">{value.toLocaleString()}</div>
      <div
        className={`text-xs ${accent === 'warning' ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground'}`}
      >
        {label}
      </div>
    </div>
  )
}

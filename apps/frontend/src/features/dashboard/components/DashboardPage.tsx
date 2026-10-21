'use client'

import { ApplicationStatusChart } from './ApplicationStatusChart'
import { MetricCard } from './MetricCard'
import { RecommendationChart } from './RecommendationChart'
import { SourceDistributionChart } from './SourceDistributionChart'
import { SourcesTable } from './SourcesTable'
import type { ApplicationStatusDistribution } from '@/entities/application/types'
import type {
  RecommendationDistribution,
  SourceDistribution,
  SourceListItem,
  SourceStats,
} from '@/entities/job/sources'

interface DashboardPageProps {
  stats: SourceStats | undefined
  statsError?: unknown
  distribution: SourceDistribution | undefined
  statsLoading: boolean
  distributionLoading: boolean
  recommendations: RecommendationDistribution | undefined
  recommendationsLoading: boolean
  recommendationsError?: unknown
  applicationStatuses: ApplicationStatusDistribution | undefined
  applicationStatusesLoading: boolean
  applicationStatusesError?: unknown
  sources: SourceListItem[]
  sourcesLoading: boolean
  sourcesEmpty: boolean
  sourcesError?: unknown
  sourcesErrorMessage?: string
  page: number
  pageSize: number
  totalPages: number
  totalItems: number
  sortField: 'job_count' | 'name' | 'last_activity'
  sortOrder: 'asc' | 'desc'
  searchValue: string
  onSearchChange: (value: string) => void
  onSortChange: (field: 'job_count' | 'name' | 'last_activity') => void
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  onRetrySources?: () => void
  onRetryDistribution?: () => void
  onRetryRecommendations?: () => void
  onRetryApplicationStatuses?: () => void
}

export function DashboardPage(props: DashboardPageProps) {
  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <header>
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Where your listings come from, how they are distributed, and where your
          applications stand.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Total listings" value={props.stats?.total_jobs ?? 0} />
        <MetricCard label="Total sources" value={props.stats?.total_sources ?? 0} />
        <MetricCard label="Active sources" value={props.stats?.active_sources ?? 0} />
        <MetricCard
          label="Unknown source"
          value={props.stats?.unknown_jobs ?? 0}
          accent={props.statsError ? 'default' : 'warning'}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border bg-card p-4 shadow-sm" data-testid="distribution-panel">
          <h2 className="mb-2 text-sm font-medium">Listings by source</h2>
          {props.statsError ? (
            <div className="p-4 text-center text-sm" role="alert">
              <p className="text-destructive">Unable to load distribution.</p>
              {props.onRetryDistribution && (
                <button
                  type="button"
                  className="mt-2 text-xs underline underline-offset-2"
                  onClick={props.onRetryDistribution}
                >
                  Retry
                </button>
              )}
            </div>
          ) : (
            <SourceDistributionChart
              distribution={props.distribution}
              isLoading={props.statsLoading || props.distributionLoading}
            />
          )}
        </section>

        <section
          className="rounded-lg border bg-card p-4 shadow-sm"
          data-testid="recommendation-panel"
        >
          <h2 className="mb-2 text-sm font-medium">Jobs by recommendation</h2>
          {props.recommendationsError ? (
            <div className="p-4 text-center text-sm" role="alert">
              <p className="text-destructive">Unable to load recommendations.</p>
              {props.onRetryRecommendations && (
                <button
                  type="button"
                  className="mt-2 text-xs underline underline-offset-2"
                  onClick={props.onRetryRecommendations}
                >
                  Retry
                </button>
              )}
            </div>
          ) : (
            <RecommendationChart
              distribution={props.recommendations}
              isLoading={props.recommendationsLoading}
            />
          )}
        </section>

        <section
          className="rounded-lg border bg-card p-4 shadow-sm"
          data-testid="application-status-panel"
        >
          <h2 className="mb-2 text-sm font-medium">Applications by status</h2>
          {props.applicationStatusesError ? (
            <div className="p-4 text-center text-sm" role="alert">
              <p className="text-destructive">Unable to load application statuses.</p>
              {props.onRetryApplicationStatuses && (
                <button
                  type="button"
                  className="mt-2 text-xs underline underline-offset-2"
                  onClick={props.onRetryApplicationStatuses}
                >
                  Retry
                </button>
              )}
            </div>
          ) : (
            <ApplicationStatusChart
              distribution={props.applicationStatuses}
              isLoading={props.applicationStatusesLoading}
            />
          )}
        </section>

        <SourcesTable
          items={props.sources}
          isLoading={props.sourcesLoading}
          isEmpty={props.sourcesEmpty}
          isError={!!props.sourcesError}
          errorMessage={props.sourcesErrorMessage}
          page={props.page}
          pageSize={props.pageSize}
          totalPages={props.totalPages}
          totalItems={props.totalItems}
          sortField={props.sortField}
          sortOrder={props.sortOrder}
          searchValue={props.searchValue}
          onSearchChange={props.onSearchChange}
          onSortChange={props.onSortChange}
          onPageChange={props.onPageChange}
          onPageSizeChange={props.onPageSizeChange}
          onRetry={props.onRetrySources}
        />
      </div>
    </div>
  )
}

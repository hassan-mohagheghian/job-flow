'use client'

import MainLayout from '@/widgets/main-layout'
import { DashboardPage } from '@/features/dashboard/components/DashboardPage'
import {
  useApplicationStatusDistribution,
  useRecommendationDistribution,
  useSourceDistribution,
  useSourceStats,
  useSourcesList,
} from '@/features/dashboard/hooks/useSources'
import { ApiError } from '@/shared/api/http-client'

function DashboardAdapter() {
  const sources = useSourcesList()
  const stats = useSourceStats()
  const distribution = useSourceDistribution()
  const recommendations = useRecommendationDistribution()
  const applicationStatuses = useApplicationStatusDistribution()

  return (
    <DashboardPage
      stats={stats.data}
      statsError={stats.isError ? stats.error : undefined}
      distribution={distribution.data}
      statsLoading={stats.isLoading}
      distributionLoading={distribution.isLoading}
      recommendations={recommendations.data}
      recommendationsLoading={recommendations.isLoading}
      recommendationsError={recommendations.isError ? recommendations.error : undefined}
      applicationStatuses={applicationStatuses.data}
      applicationStatusesLoading={applicationStatuses.isLoading}
      applicationStatusesError={
        applicationStatuses.isError ? applicationStatuses.error : undefined
      }
      onRetryApplicationStatuses={applicationStatuses.refetch}
      onRetryDistribution={() => {
        stats.refetch()
        distribution.refetch()
      }}
      onRetryRecommendations={recommendations.refetch}
      sources={sources.data?.items ?? []}
      sourcesLoading={sources.isLoading}
      sourcesEmpty={!sources.isLoading && (sources.data?.items.length ?? 0) === 0}
      sourcesError={sources.isError ? sources.error : undefined}
      sourcesErrorMessage={
        sources.error instanceof ApiError ? String(sources.error.message) : undefined
      }
      page={sources.query.page}
      pageSize={sources.query.page_size}
      totalPages={sources.data?.pagination.total_pages ?? 1}
      totalItems={sources.data?.pagination.total_items ?? 0}
      sortField={sources.query.field}
      sortOrder={sources.query.order}
      searchValue={sources.rawSearch}
      onSearchChange={sources.setSearch}
      onSortChange={sources.onSortChange}
      onPageChange={sources.setPage}
      onPageSizeChange={sources.setPageSize}
      onRetrySources={sources.refetch}
    />
  )
}

export default function DashboardPageWidget() {
  return (
    <MainLayout>
      <DashboardAdapter />
    </MainLayout>
  )
}

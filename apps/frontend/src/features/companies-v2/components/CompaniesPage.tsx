'use client'

import { useCallback } from 'react'
import type { CompanyListItem } from '@/entities/company/types'
import { Button } from '@/shared/ui/button'
import { CompaniesHeader } from './CompaniesHeader'
import { CompaniesToolbar } from './CompaniesToolbar'
import { CompaniesTable } from './CompaniesTable'
import { CompanyDetailDrawer } from './CompanyDetailDrawer'
import { CompanyEditDrawer } from './CompanyEditDrawer'
import CreateEntityDrawer, { type CreateEntityFormData } from '@/shared/components/CreateEntityDrawer'
import { ProcessingDrawer } from '@/shared/components/ProcessingDrawer'
import { useCreateCompany } from '@/features/companies-v2/hooks/useCreateCompany'
import { toast } from 'sonner'

interface CompaniesPageProps {
  items: CompanyListItem[]
  total: number
  loadedCount: number
  isLoading: boolean
  isFetchingNextPage: boolean
  hasNextPage: boolean
  onFetchNextPage: () => void
  isError: boolean
  error: Error | null
  onRefetch: () => void
  isRefetching?: boolean
  query: string
  onQueryChange: (value: string) => void
  sort: string
  onSortChange: (value: string) => void
  order: 'asc' | 'desc'
  filterIndustry: string
  onFilterIndustryChange: (value: string) => void
  filterCompanyType: string
  onFilterCompanyTypeChange: (value: string) => void
  filterStatus: string
  onFilterStatusChange: (value: string) => void
  filterPinned: boolean
  onFilterPinnedChange: (value: boolean) => void
  activeFilterCount: number
  onClearFilters: () => void
  onViewDetails: (id: string) => void
  onReprocess: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTogglePinned: (id: string, pinned: boolean) => void
  showRowNumberColumn?: boolean
  onToggleRowNumberColumn?: (value: boolean) => void
  onRelate: (companyId: string, mainCompanyId: string | null) => void
  relatePending: boolean
  queueDrawerOpen: boolean
  onQueueDrawerOpenChange: (open: boolean) => void
  addCompanyDrawerOpen: boolean
  onAddCompanyDrawerOpenChange: (open: boolean) => void
  detailCompanyId: string | null
  onDetailCompanyIdChange: (id: string | null) => void
  editCompanyId: string | null
  onEditCompanyIdChange: (id: string | null) => void
  onOpenJob?: (id: string) => void
  onNavigateToJob?: (id: string) => void
}

export function CompaniesPage({
  items, total, loadedCount, isLoading, isFetchingNextPage, hasNextPage, onFetchNextPage,
  isError, error, onRefetch, isRefetching,
  query, onQueryChange,
  sort, onSortChange, order,
  filterIndustry, onFilterIndustryChange,
  filterCompanyType, onFilterCompanyTypeChange,
  filterStatus, onFilterStatusChange,
  filterPinned, onFilterPinnedChange,
  activeFilterCount, onClearFilters,
  onViewDetails, onReprocess, onEdit, onDelete, onTogglePinned,
  showRowNumberColumn = false, onToggleRowNumberColumn,
  onRelate, relatePending,
  queueDrawerOpen, onQueueDrawerOpenChange,
  addCompanyDrawerOpen, onAddCompanyDrawerOpenChange,
  detailCompanyId, onDetailCompanyIdChange,
  editCompanyId, onEditCompanyIdChange,
  onOpenJob, onNavigateToJob,
}: CompaniesPageProps) {
  const { createCompany, submitting, error: createError, clearError } = useCreateCompany()

  const handleCreateCompany = useCallback(async (data: CreateEntityFormData) => {
    const links = data.primaryLink ? [data.primaryLink, ...data.links] : data.links
    const ok = await createCompany({
      name: data.name || data.primaryLink?.url,
      notes: data.notes.map((n) => ({ content: n.content })),
      links: links.map((l) => ({ url: l.url, title: l.title })),
      source: 'web',
      queue: data.queue,
    })
    if (ok) {
      toast.success(data.queue ? 'Company added and queued' : 'Company added to list')
      onAddCompanyDrawerOpenChange(false)
    }
  }, [createCompany, onAddCompanyDrawerOpenChange])

  if (isError) {
    return (
      <div className="flex flex-col h-full rounded-lg border overflow-hidden bg-card">
        <CompaniesHeader
          total={total}
          loadedCount={loadedCount}
          onOpenQueue={() => onQueueDrawerOpenChange(true)}
          onAddCompany={() => onAddCompanyDrawerOpenChange(true)}
          onRefresh={onRefetch}
          isRefreshing={isRefetching}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <p className="text-sm text-red-500">Unable to load companies</p>
            <p className="text-xs text-muted-foreground">{error?.message || 'An unexpected error occurred'}</p>
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onRefetch}>
              Retry
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full rounded-lg border overflow-hidden bg-card">
      <CompaniesHeader
        total={total}
        loadedCount={loadedCount}
        onOpenQueue={() => onQueueDrawerOpenChange(true)}
        onAddCompany={() => onAddCompanyDrawerOpenChange(true)}
        onRefresh={onRefetch}
        isRefreshing={isRefetching}
      />
      <CompaniesToolbar
        query={query}
        onQueryChange={onQueryChange}
        filterIndustry={filterIndustry}
        onFilterIndustryChange={onFilterIndustryChange}
        filterCompanyType={filterCompanyType}
        onFilterCompanyTypeChange={onFilterCompanyTypeChange}
        filterStatus={filterStatus}
        onFilterStatusChange={onFilterStatusChange}
        filterPinned={filterPinned}
        onFilterPinnedChange={onFilterPinnedChange}
        items={items}
        activeFilterCount={activeFilterCount}
        onClearFilters={onClearFilters}
        showRowNumberColumn={showRowNumberColumn}
        onToggleRowNumberColumn={onToggleRowNumberColumn}
      />
      <CompaniesTable
        items={items}
        total={total}
        loadedCount={loadedCount}
        isLoading={isLoading}
        isFetchingNextPage={isFetchingNextPage}
        hasNextPage={hasNextPage}
        onFetchNextPage={onFetchNextPage}
        onViewDetails={onViewDetails}
        onReprocess={onReprocess}
        onEdit={onEdit}
        onDelete={onDelete}
        showRowNumberColumn={showRowNumberColumn}
        sort={sort}
        order={order}
        onSortChange={onSortChange}
      />
      <ProcessingDrawer
        open={queueDrawerOpen}
        onOpenChange={onQueueDrawerOpenChange}
        targetType="company"
      />
      <CompanyDetailDrawer
        companyId={detailCompanyId}
        onOpenChange={onDetailCompanyIdChange}
        onReprocess={onReprocess}
        onEdit={onEdit}
        onTogglePinned={onTogglePinned}
        onRelate={onRelate}
        relatePending={relatePending}
        onOpenJob={onOpenJob}
        onNavigateToJob={onNavigateToJob}
      />
      <CompanyEditDrawer
        companyId={editCompanyId}
        onOpenChange={onEditCompanyIdChange}
      />
      <CreateEntityDrawer
        mode="company"
        open={addCompanyDrawerOpen}
        onOpenChange={(open) => { onAddCompanyDrawerOpenChange(open); if (!open) clearError() }}
        onSubmit={handleCreateCompany}
        submitting={submitting}
        error={createError}
      />
    </div>
  )
}

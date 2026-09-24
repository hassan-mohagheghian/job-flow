'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { SkillListItem } from '@/entities/skill/types'
import { Button } from '@/shared/ui/button'
import { SkillsHeader } from './SkillsHeader'
import { SkillsToolbar } from './SkillsToolbar'
import { SkillsTable } from './SkillsTable'
import { SkillDetailDrawer } from './SkillDetailDrawer'
import { SkillEditDrawer } from './SkillEditDrawer'
import { BreakdownSkillDialog } from './BreakdownSkillDialog'
import AddSkillDrawer from './AddSkillDrawer'
import { useBreakdownSkill, useCreateSkill, useMergeSkills } from '@/entities/skill/hooks'
import { toast } from 'sonner'
import { MergeSkillDialog } from './MergeSkillDialog'

interface SkillsPageProps {
  items: SkillListItem[]
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
  filterCategories: string[]
  onFilterCategoriesChange: (value: string[]) => void
  categoryOptions: string[]
  filterPinned?: boolean
  onFilterPinnedChange?: (value: boolean) => void
  activeFilterCount: number
  onClearFilters: () => void
  onViewDetails: (id: number) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
  onTogglePinned?: (id: number, pinned: boolean) => void
  showSelectColumn?: boolean
  onToggleSelectColumn?: (value: boolean) => void
  showRowNumberColumn?: boolean
  onToggleRowNumberColumn?: (value: boolean) => void
  addSkillDrawerOpen: boolean
  onAddSkillDrawerOpenChange: (open: boolean) => void
  detailSkillId: number | null
  onDetailSkillIdChange: (id: number | null) => void
  editSkillId: number | null
  onEditSkillIdChange: (id: number | null) => void
  onOpenJob?: (id: string) => void
}

export function SkillsPage({
  items, total, loadedCount, isLoading, isFetchingNextPage, hasNextPage, onFetchNextPage,
  isError, error, onRefetch, isRefetching,
  query, onQueryChange,
  sort, onSortChange, order,
  filterCategories, onFilterCategoriesChange, categoryOptions,
  filterPinned = false, onFilterPinnedChange,
  activeFilterCount, onClearFilters,
  onViewDetails, onEdit, onDelete, onTogglePinned,
  showSelectColumn = false, onToggleSelectColumn,
  showRowNumberColumn = false, onToggleRowNumberColumn,
  addSkillDrawerOpen, onAddSkillDrawerOpenChange,
  detailSkillId, onDetailSkillIdChange,
  editSkillId, onEditSkillIdChange,
  onOpenJob,
}: SkillsPageProps) {
  const { createSkill, submitting, error: createError, clearError } = useCreateSkill()
  const mergeMutation = useMergeSkills()
  const breakdownMutation = useBreakdownSkill()

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [mergeOpen, setMergeOpen] = useState(false)
  const [rowMergeSkill, setRowMergeSkill] = useState<{ id: number; name: string } | null>(null)
  const [breakdownSkill, setBreakdownSkill] = useState<{ id: number; name: string } | null>(null)

  useEffect(() => {
    setSelectedIds(new Set())
  }, [query, filterCategories, filterPinned])

  const loadedIds = useMemo(() => new Set(items.map((s) => s.id)), [items])
  useEffect(() => {
    setSelectedIds((prev) => {
      const next = new Set([...prev].filter((id) => loadedIds.has(id)))
      return next.size === prev.size ? prev : next
    })
  }, [loadedIds])

  const handleToggleSelect = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleToggleSelectAll = useCallback((selectAll: boolean) => {
    setSelectedIds(selectAll ? new Set(loadedIds) : new Set())
  }, [loadedIds])

  const handleClearSelection = useCallback(() => setSelectedIds(new Set()), [])

  const selectedSkills = useMemo(
    () => items.filter((s) => selectedIds.has(s.id)),
    [items, selectedIds]
  )

  const handleBulkMerge = useCallback(async (targetId: number) => {
    const sourceIds = [...selectedIds]
    if (sourceIds.length === 0) return
    setMergeOpen(false)
    try {
      await mergeMutation.mutateAsync({ targetId, sourceIds })
      toast.success(`Merged ${sourceIds.length} skill${sourceIds.length !== 1 ? 's' : ''}`)
      setSelectedIds(new Set())
      if (editSkillId != null && sourceIds.includes(editSkillId)) onEditSkillIdChange(null)
    } catch {
      toast.error('Failed to merge skills')
    }
  }, [selectedIds, mergeMutation, editSkillId, onEditSkillIdChange])

  const handleRowMerge = useCallback(async (targetId: number) => {
    const skill = rowMergeSkill
    if (!skill) return
    setRowMergeSkill(null)
    try {
      await mergeMutation.mutateAsync({ targetId, sourceIds: [skill.id] })
      toast.success(`Merged "${skill.name}"`)
      if (detailSkillId === skill.id) onDetailSkillIdChange(null)
      if (editSkillId === skill.id) onEditSkillIdChange(null)
    } catch {
      toast.error('Failed to merge skill')
    }
  }, [rowMergeSkill, mergeMutation, detailSkillId, editSkillId, onDetailSkillIdChange, onEditSkillIdChange])

  const handleBreakDown = useCallback(async (childNames: string[]) => {
    const skill = breakdownSkill
    if (!skill) return
    setBreakdownSkill(null)
    try {
      await breakdownMutation.mutateAsync({ id: skill.id, childNames })
      toast.success(`Broke "${skill.name}" down into ${childNames.length} skills`)
      if (detailSkillId === skill.id) onDetailSkillIdChange(null)
      if (editSkillId === skill.id) onEditSkillIdChange(null)
    } catch {
      toast.error('Failed to break down skill')
    }
  }, [breakdownSkill, breakdownMutation, detailSkillId, editSkillId, onDetailSkillIdChange, onEditSkillIdChange])

  const handleCreateSkill = useCallback(async (data: { name: string; level: number; roles: string; path: string; category: string; categories: string[] }) => {
    const ok = await createSkill({
      name: data.name,
      level: data.level,
      roles: data.roles,
      path: data.path,
      category: data.category,
      categories: data.categories,
    })
    if (ok) {
      toast.success('Skill added')
      onAddSkillDrawerOpenChange(false)
    }
  }, [createSkill, onAddSkillDrawerOpenChange])

  const detailSkill = items.find((s) => s.id === detailSkillId) ?? null

  if (isError) {
    return (
      <div className="flex flex-col h-full rounded-lg border overflow-hidden bg-card">
        <SkillsHeader
          total={total}
          loadedCount={loadedCount}
          onAddSkill={() => onAddSkillDrawerOpenChange(true)}
          onRefresh={onRefetch}
          isRefreshing={isRefetching}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <p className="text-sm text-red-500">Unable to load skills</p>
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
      <SkillsHeader
        total={total}
        loadedCount={loadedCount}
        onAddSkill={() => onAddSkillDrawerOpenChange(true)}
        onRefresh={onRefetch}
        isRefreshing={isRefetching}
      />
      <SkillsToolbar
        query={query}
        onQueryChange={onQueryChange}
        filterCategories={filterCategories}
        onFilterCategoriesChange={onFilterCategoriesChange}
        categoryOptions={categoryOptions}
        filterPinned={filterPinned}
        onFilterPinnedChange={onFilterPinnedChange}
        activeFilterCount={activeFilterCount}
        onClearFilters={onClearFilters}
        showSelectColumn={showSelectColumn}
        onToggleSelectColumn={onToggleSelectColumn}
        showRowNumberColumn={showRowNumberColumn}
        onToggleRowNumberColumn={onToggleRowNumberColumn}
        selectedCount={selectedIds.size}
        onMergeSelected={() => setMergeOpen(true)}
        onClearSelection={handleClearSelection}
        mergePending={mergeMutation.isPending}
      />
      <SkillsTable
        items={items}
        total={total}
        loadedCount={loadedCount}
        isLoading={isLoading}
        isFetchingNextPage={isFetchingNextPage}
        hasNextPage={hasNextPage}
        onFetchNextPage={onFetchNextPage}
        onViewDetails={onViewDetails}
        onEdit={onEdit}
        onDelete={onDelete}
        onBreakDown={(id) => {
          const skill = items.find((s) => s.id === id)
          if (skill) setBreakdownSkill({ id: skill.id, name: skill.name })
        }}
        onMerge={(id) => {
          const skill = items.find((s) => s.id === id)
          if (skill) setRowMergeSkill({ id: skill.id, name: skill.name })
        }}
        showSelectColumn={showSelectColumn}
        showRowNumberColumn={showRowNumberColumn}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        onToggleSelectAll={handleToggleSelectAll}
        sort={sort}
        order={order}
        onSortChange={onSortChange}
      />
      <SkillDetailDrawer
        skillId={detailSkillId}
        skill={detailSkill}
        onOpenChange={onDetailSkillIdChange}
        onEdit={onEdit}
        onDelete={onDelete}
        onTogglePinned={onTogglePinned}
        onBreakDown={(id) => {
          const skill = items.find((s) => s.id === id)
          if (skill) setBreakdownSkill({ id: skill.id, name: skill.name })
        }}
        onOpenJob={onOpenJob}
      />
      <SkillEditDrawer
        skillId={editSkillId}
        onOpenChange={onEditSkillIdChange}
      />
      <BreakdownSkillDialog
        skill={breakdownSkill}
        open={breakdownSkill != null}
        onOpenChange={(open) => { if (!open) setBreakdownSkill(null) }}
        onBreakDown={handleBreakDown}
        pending={breakdownMutation.isPending}
      />
      <MergeSkillDialog
        sources={selectedSkills.map((s) => ({ id: s.id, name: s.name }))}
        open={mergeOpen}
        onOpenChange={setMergeOpen}
        onMerge={handleBulkMerge}
        pending={mergeMutation.isPending}
      />
      <MergeSkillDialog
        sources={rowMergeSkill ? [{ id: rowMergeSkill.id, name: rowMergeSkill.name }] : []}
        open={rowMergeSkill != null}
        onOpenChange={(open) => { if (!open) setRowMergeSkill(null) }}
        onMerge={handleRowMerge}
        pending={mergeMutation.isPending}
      />
      <AddSkillDrawer
        open={addSkillDrawerOpen}
        onOpenChange={(open) => { onAddSkillDrawerOpenChange(open); if (!open) clearError() }}
        onSubmit={handleCreateSkill}
        submitting={submitting}
        error={createError}
      />
    </div>
  )
}

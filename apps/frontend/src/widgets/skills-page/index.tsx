'use client'

import dynamic from 'next/dynamic'
import MainLayout from '@/widgets/main-layout'
import { useState, useCallback, useMemo, useEffect } from 'react'
import { useSkillsInfiniteQuery, useSkillCategories } from '@/entities/skill/hooks'
import ConfirmDialog, { useConfirmDialog } from '@/shared/components/ConfirmDialog'
import { toast } from 'sonner'
import { setSearchParam, getSearchParam } from '@/shared/lib/url'

const SkillsPageContent = dynamic(
  () => import('@/features/skills-v2/components/SkillsPage').then(m => ({ default: m.SkillsPage })),
  { ssr: false }
)

function SkillsPageAdapter() {
  const [addSkillDrawerOpen, setAddSkillDrawerOpen] = useState(false)
  const [detailSkillId, setDetailSkillId] = useState<number | null>(null)
  const [editSkillId, setEditSkillId] = useState<number | null>(null)
  const [showSelectColumn, setShowSelectColumn] = useState(false)
  const [showRowNumberColumn, setShowRowNumberColumn] = useState(true)
  const { dialog: confirmDialog, showConfirm, onClose: closeConfirm } = useConfirmDialog()

  const {
    items, total, loadedCount, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage,
    isError, error, refetch, isRefetching,
    query, setQuery,
    sort, order, handleHeaderSort,
    filterCategories, setFilterCategories,
    filterPinned, setFilterPinned,
    activeFilterCount, clearFilters,
    deleteMutation, pinnedMutation,
  } = useSkillsInfiniteQuery()

  const { categories } = useSkillCategories()

  const categoryOptions = useMemo(() => categories.map((c) => c.category), [categories])

  const handleViewDetails = useCallback((id: number) => {
    setDetailSkillId(id)
    setSearchParam('skill', String(id))
  }, [])

  const handleOpenJob = useCallback((id: string) => {
    window.location.href = `/jobs?job=${encodeURIComponent(id)}`
  }, [])

  const handleTogglePinned = useCallback((id: number, pinned: boolean) => {
    pinnedMutation.mutate({ id, pinned })
  }, [pinnedMutation])

  const handleEdit = useCallback((id: number) => {
    setEditSkillId(id)
  }, [])

  const handleDelete = useCallback(async (id: number) => {
    const skill = items.find((s) => s.id === id)
    const ok = await showConfirm(
      'Delete Skill',
      `Permanently delete "${skill?.name ?? 'this skill'}" and all its aliases?`,
      'Delete',
    )
    if (!ok) return
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success('Skill deleted')
        setDetailSkillId((current) => (current === id ? null : current))
        setEditSkillId((current) => (current === id ? null : current))
        setSearchParam('skill', null)
      },
      onError: () => {
        toast.error('Failed to delete skill')
      },
    })
  }, [showConfirm, deleteMutation, items])

  useEffect(() => {
    const skillId = getSearchParam('skill')
    if (skillId) {
      const parsed = Number(skillId)
      if (!Number.isNaN(parsed)) setDetailSkillId(parsed)
    }
  }, [])

  useEffect(() => {
    if (detailSkillId === null) setSearchParam('skill', null)
  }, [detailSkillId])

  return (
    <div className="flex flex-col h-full">
      <SkillsPageContent
        items={items}
        total={total}
        loadedCount={loadedCount}
        isLoading={isLoading}
        isFetchingNextPage={isFetchingNextPage}
        hasNextPage={hasNextPage}
        onFetchNextPage={fetchNextPage}
        isError={isError}
        error={error}
        onRefetch={refetch}
        isRefetching={isRefetching}
        query={query}
        onQueryChange={setQuery}
        sort={sort}
        onSortChange={handleHeaderSort}
        order={order}
        filterCategories={filterCategories}
        onFilterCategoriesChange={setFilterCategories}
        categoryOptions={categoryOptions}
        filterPinned={filterPinned}
        onFilterPinnedChange={setFilterPinned}
        activeFilterCount={activeFilterCount}
        onClearFilters={clearFilters}
        onViewDetails={handleViewDetails}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onTogglePinned={handleTogglePinned}
        showSelectColumn={showSelectColumn}
        onToggleSelectColumn={setShowSelectColumn}
        showRowNumberColumn={showRowNumberColumn}
        onToggleRowNumberColumn={setShowRowNumberColumn}
        addSkillDrawerOpen={addSkillDrawerOpen}
        onAddSkillDrawerOpenChange={setAddSkillDrawerOpen}
        detailSkillId={detailSkillId}
        onDetailSkillIdChange={(id) => {
          setDetailSkillId(id)
          if (id === null) setSearchParam('skill', null)
        }}
        editSkillId={editSkillId}
        onEditSkillIdChange={setEditSkillId}
        onOpenJob={handleOpenJob}
      />
      <ConfirmDialog dialog={confirmDialog} onClose={closeConfirm} />
    </div>
  )
}

export default function SkillsPageWidget() {
  return (
    <MainLayout>
      <SkillsPageAdapter />
    </MainLayout>
  )
}

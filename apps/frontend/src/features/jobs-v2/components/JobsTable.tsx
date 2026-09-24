import { useRef, useCallback, useEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import type { JobListItem } from '@/entities/job/types'
import { JobRow } from './JobRow'
import { SortableHeader, type ScoreSortOption } from './SortableHeader'
import { ColumnResizeHandle } from './ColumnResizeHandle'
import { COLUMN_GRID_TEMPLATE, LEADING_COLUMN_WIDTH } from './jobsColumns'
import { useColumnResize } from '../hooks/useColumnResize'

const ESTIMATED_ROW_HEIGHT = 40

interface JobsTableProps {
  items: JobListItem[]
  total: number
  loadedCount?: number
  isLoading: boolean
  isFetchingNextPage?: boolean
  hasNextPage?: boolean
  onFetchNextPage?: () => void
  onProcessV2: (id: string) => void
  onViewDetails: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onRetry?: (id: string) => void
  onCancel?: (id: string) => void
  onApplication?: (id: string) => void
  showRowNumberColumn?: boolean
  sort?: string
  order?: 'asc' | 'desc'
  onSortChange?: (field: string) => void
}

const SCORE_SORT_OPTIONS: ScoreSortOption[] = [
  { field: 'overall_score', label: 'Overall' },
  { field: 'fit_score', label: 'Fit' },
  { field: 'success_score', label: 'Success' },
]

interface ColumnDef {
  label: string
  field?: string
  scoreOptions?: ScoreSortOption[]
}

const ROW_NUMBER_COLUMN: ColumnDef = { label: '#' }

const COLUMN_DEFS: ColumnDef[] = [
  { label: 'Title', field: 'title' },
  { label: 'Company', field: 'company' },
  { label: 'Location' },
  { label: 'Scores', scoreOptions: SCORE_SORT_OPTIONS },
  { label: 'Rec' },
  { label: 'Tags' },
  { label: 'Status', field: 'status' },
  { label: 'Tracking' },
  { label: 'Updated', field: 'updated_at' },
  { label: 'Created', field: 'created_at' },
]

export function JobsTable({
  items, total, loadedCount = 0, isLoading, isFetchingNextPage = false, hasNextPage = false, onFetchNextPage = () => {},
  onProcessV2, onViewDetails, onEdit, onDelete, onRetry, onCancel, onApplication,
  showRowNumberColumn = false,
  sort = 'created_at', order = 'desc', onSortChange = () => {},
}: JobsTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const rowCount = isLoading ? 8 : items.length

  const defaultTemplate = [
    ...(showRowNumberColumn ? [LEADING_COLUMN_WIDTH] : []),
    COLUMN_GRID_TEMPLATE,
  ].join(' ')

  const { gridTemplate, onResize, onResizeStart, onResizeEnd } = useColumnResize(defaultTemplate)

  const visibleColumnDefs = [
    ...(showRowNumberColumn ? [ROW_NUMBER_COLUMN] : []),
    ...COLUMN_DEFS,
  ]
  const gridStyle = { gridTemplateColumns: gridTemplate }

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ESTIMATED_ROW_HEIGHT,
    overscan: 10,
    measureElement: (element) => element.getBoundingClientRect().height,
  })

  const sentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || !hasNextPage) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          onFetchNextPage()
        }
      },
      { rootMargin: '200px' }
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, onFetchNextPage])

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto" ref={scrollRef}>
        <div className="w-full">
          <div className="sticky top-0 z-10 bg-card grid border-b border-border/40" style={gridStyle}>
            {visibleColumnDefs.map((col, i) => (
              <div key={col.label} className="py-2 px-3 flex items-center relative group/header">
                <SortableHeader
                  label={col.label}
                  field={col.field}
                  scoreOptions={col.scoreOptions}
                  sort={sort}
                  order={order}
                  onSortChange={onSortChange}
                />
                <ColumnResizeHandle
                  colIndex={i}
                  onResize={onResize}
                  onResizeStart={onResizeStart}
                  onResizeEnd={onResizeEnd}
                />
              </div>
            ))}
          </div>
          <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
            {virtualizer.getVirtualItems().map(virtualItem => (
              <div
                key={virtualItem.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualItem.start}px)`,
                  gridTemplateColumns: gridTemplate,
                }}
                data-index={virtualItem.index}
                ref={virtualizer.measureElement}
                className="grid border-b border-border/40"
              >
                {visibleColumnDefs.map((_, j) => (
                  <div key={j} className="py-2 px-3">
                    <div className="h-3 bg-muted rounded animate-pulse" style={{ width: `${50 + Math.random() * 40}%` }} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!isLoading && items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">No jobs have been imported yet.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto" ref={scrollRef}>
      <div className="w-full">
        <div className="sticky top-0 z-10 bg-card grid border-b border-border/40" style={gridStyle}>
          {visibleColumnDefs.map((col, i) => (
            <div key={col.label} className="py-2 px-3 flex items-center relative group/header">
              <SortableHeader
                label={col.label}
                field={col.field}
                scoreOptions={col.scoreOptions}
                sort={sort}
                order={order}
                onSortChange={onSortChange}
              />
              <ColumnResizeHandle
                colIndex={i}
                onResize={onResize}
                onResizeStart={onResizeStart}
                onResizeEnd={onResizeEnd}
              />
            </div>
          ))}
        </div>
        <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
          {virtualizer.getVirtualItems().map(virtualItem => {
            const job = items[virtualItem.index]
            if (!job) return null
            return (
              <div
                key={virtualItem.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualItem.start}px)`,
                }}
                data-index={virtualItem.index}
                ref={virtualizer.measureElement}
              >
                <JobRow
                  job={job}
                  onProcessV2={onProcessV2}
                  onViewDetails={onViewDetails}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onRetry={onRetry}
                  onCancel={onCancel}
                  onApplication={onApplication}
                  showRowNumberColumn={showRowNumberColumn}
                  rowNumber={virtualItem.index + 1}
                  gridTemplate={gridTemplate}
                />
              </div>
            )
          })}
        </div>
        <div ref={sentinelRef} className="h-4" />
        <div className="px-3 py-3 text-center">
          {isFetchingNextPage && (
            <p className="text-xs text-muted-foreground animate-pulse">Loading more jobs...</p>
          )}
          {!hasNextPage && !isFetchingNextPage && items.length > 0 && (
            <div className="text-xs text-muted-foreground">
              <p>You've reached the end</p>
              <p>{total} jobs loaded</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

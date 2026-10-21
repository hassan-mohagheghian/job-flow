'use client'

import { useState } from 'react'
import { MagnifyingGlass } from '@phosphor-icons/react'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import { SortableHeader } from '@/features/jobs-v2/components/SortableHeader'
import type { SourceListItem, SourceSortField } from '@/entities/job/sources'
import { PAGE_SIZE_OPTIONS } from '@/shared/config/constants'
import { formatTimeAgo } from '@/shared/lib/formatTimeAgo'

interface SourcesTableProps {
  items: SourceListItem[]
  isLoading: boolean
  isEmpty: boolean
  isError?: boolean
  errorMessage?: string
  page: number
  pageSize: number
  totalPages: number
  totalItems: number
  sortField: SourceSortField['field']
  sortOrder: SourceSortField['order']
  searchValue: string
  onSearchChange: (value: string) => void
  onSortChange: (field: SourceSortField['field']) => void
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  onRetry?: () => void
}

const Spacer = () => <span className="flex-1" />

export function SourcesTable(props: SourcesTableProps) {
  const [localSearch, setLocalSearch] = useState(props.searchValue)

  const handleSearch = (value: string) => {
    setLocalSearch(value)
    props.onSearchChange(value)
  }

  return (
    <section className="rounded-lg border bg-card shadow-sm" data-testid="sources-table">
      <header className="flex flex-wrap items-center gap-2 border-b p-3">
        <h2 className="text-sm font-medium">Sources</h2>
        <Spacer />
        <div className="relative w-full max-w-64 sm:w-64">
          <MagnifyingGlass
            className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground"
            size={16}
            aria-hidden
          />
          <Input
            aria-label="Search sources"
            placeholder="Search sources…"
            className="pl-8 h-8"
            value={localSearch}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
      </header>

      {props.isError ? (
        <div className="p-6 text-center text-sm" role="alert">
          <p className="text-destructive">Unable to load sources.</p>
          {props.errorMessage && <p className="mt-1 text-muted-foreground">{props.errorMessage}</p>}
          {props.onRetry && (
            <Button variant="outline" size="sm" className="mt-3" onClick={props.onRetry}>
              Retry
            </Button>
          )}
        </div>
      ) : props.isLoading ? (
        <div className="p-4 space-y-2" data-testid="sources-table-loading">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-muted" />
          ))}
        </div>
      ) : props.isEmpty ? (
        <div className="p-6 text-center text-sm text-muted-foreground">
          No sources yet — import jobs to populate the dashboard.
        </div>
      ) : (
        <>
          {/* Desktop grid table */}
          <div className="hidden sm:grid grid-cols-[1fr_1fr_6rem_7rem] gap-x-4 px-3 py-2 text-xs text-muted-foreground">
            <SortableHeader
              label="Source"
              field="name"
              sort={props.sortField}
              order={props.sortOrder}
              onSortChange={props.onSortChange}
            />
            <div className="text-2xs font-medium uppercase tracking-wider">Website</div>
            <SortableHeader
              label="Jobs"
              field="job_count"
              sort={props.sortField}
              order={props.sortOrder}
              onSortChange={props.onSortChange}
            />
            <SortableHeader
              label="Last activity"
              field="last_activity"
              sort={props.sortField}
              order={props.sortOrder}
              onSortChange={props.onSortChange}
            />
          </div>

          <ul className="divide-y">
            {props.items.map((source) => (
              <li
                key={source.id}
                data-testid="source-row"
                className="grid gap-1 px-3 py-2.5 sm:grid-cols-[1fr_1fr_6rem_7rem] sm:items-center sm:gap-x-4"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="truncate text-sm font-medium">{source.name}</span>
                  {!source.is_active && <Badge variant="secondary">Inactive</Badge>}
                </div>
                <div className="text-sm truncate">
                  {source.canonical_url ? (
                    <a
                      href={source.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary underline-offset-2 hover:underline"
                      title={source.canonical_url}
                    >
                      {source.domain}
                    </a>
                  ) : (
                    <span className="text-muted-foreground">{source.domain}</span>
                  )}
                </div>
                <div className="text-sm tabular-nums">{source.job_count.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">
                  {source.last_activity
                    ? formatTimeAgo(source.last_activity)
                    : '—'}
                </div>
              </li>
            ))}
          </ul>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t p-3 text-xs text-muted-foreground">
            <span>
              Page {props.page} of {props.totalPages} • {props.totalItems.toLocaleString()} sources
            </span>
            <div className="flex items-center gap-2">
              <Select
                value={String(props.pageSize)}
                onValueChange={(value) => props.onPageSizeChange(Number(value))}
              >
                <SelectTrigger
                  aria-label="Rows per page"
                  className="h-7 w-[8.5rem] gap-1 text-xs"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} per page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                disabled={props.page <= 1}
                onClick={() => props.onPageChange(props.page - 1)}
                aria-label="Previous page"
              >
                Prev
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={props.page >= props.totalPages}
                onClick={() => props.onPageChange(props.page + 1)}
                aria-label="Next page"
              >
                Next
              </Button>
            </div>
          </footer>
        </>
      )}
    </section>
  )
}

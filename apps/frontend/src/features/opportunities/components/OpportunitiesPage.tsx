'use client'

import { useState } from 'react'
import { Button } from '@/shared/ui/button'
import { DebouncedInput } from '@/shared/ui/debounced-input'
import { Textarea } from '@/shared/ui/textarea'
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader } from '@/shared/components/Drawer'
import type { OpportunityListItem, OpportunityStatus } from '@/entities/opportunity/types'
import { OpportunityStatusBadge } from './OpportunityStatusBadge'

interface OpportunitiesPageProps {
  items: OpportunityListItem[]
  total: number
  isLoading: boolean
  isError: boolean
  onRefetch: () => void
  query: string
  onQueryChange: (query: string) => void
  filterStatus: OpportunityStatus | ''
  onFilterStatusChange: (status: OpportunityStatus | '') => void
  onOpenCreate: () => void
  onOpenDetail: (id: string) => void
  onDelete: (id: string) => void
  deletingId?: string | null
}

const STATUS_OPTIONS: (OpportunityStatus | '')[] = [
  '',
  'new',
  'extracted',
  'enriching',
  'needs_info',
  'evaluated',
  'ready_to_apply',
  'applied',
  'replied',
  'interview',
  'rejected',
  'closed',
]

export function OpportunitiesPage({
  items,
  total,
  isLoading,
  isError,
  onRefetch,
  query,
  onQueryChange,
  filterStatus,
  onFilterStatusChange,
  onOpenCreate,
  onOpenDetail,
  onDelete,
  deletingId,
}: OpportunitiesPageProps) {
  const [confirmId, setConfirmId] = useState<string | null>(null)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <div>
          <h1 className="text-lg font-semibold">Opportunities</h1>
          <p className="text-xs text-muted-foreground">
            {total} inbound {total === 1 ? 'opportunity' : 'opportunities'}
          </p>
        </div>
        <Button onClick={onOpenCreate}>＋ New Opportunity</Button>
      </div>

      <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
        <DebouncedInput
          aria-label="Search opportunities"
          placeholder="Search title, company, sender, message…"
          value={query}
          onValueChange={onQueryChange}
          className="max-w-sm"
        />
        <select
          aria-label="Filter by status"
          value={filterStatus}
          onChange={(e) => onFilterStatusChange(e.target.value as OpportunityStatus | '')}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s || 'all'} value={s}>
              {s === '' ? 'All statuses' : s.replaceAll('_', ' ')}
            </option>
          ))}
        </select>
        <Button variant="ghost" size="sm" onClick={onRefetch}>
          Refresh
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-14 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">Failed to load opportunities.</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={onRefetch}>
              Retry
            </Button>
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm font-medium">No opportunities yet</p>
            <p className="text-xs text-muted-foreground mt-1">Add your first inbound message to get started.</p>
            <Button size="sm" className="mt-3" onClick={onOpenCreate}>
              ＋ New Opportunity
            </Button>
          </div>
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50">
                <button
                  type="button"
                  onClick={() => onOpenDetail(item.id)}
                  className="flex-1 min-w-0 text-left"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-sm font-medium truncate">{item.title}</span>
                    <OpportunityStatusBadge status={item.status} />
                  </div>
                  <div className="text-xs text-muted-foreground truncate mt-0.5">
                    {[item.company_name, item.next_action].filter(Boolean).join(' · ') || '—'}
                  </div>
                </button>
                <div className="shrink-0 w-12 text-right">
                  {item.overall_score != null ? (
                    <span className="text-sm font-bold">{item.overall_score}</span>
                  ) : (
                    <span className="text-2xs text-muted-foreground uppercase">Evaluation pending</span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Delete opportunity ${item.title}`}
                  disabled={deletingId === item.id}
                  onClick={() => setConfirmId(item.id)}
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Drawer open={confirmId !== null} onOpenChange={(open) => !open && setConfirmId(null)}>
        <DrawerHeader title="Delete opportunity" />
        <DrawerContent>
          <p className="text-sm text-muted-foreground">
            Permanently delete this opportunity and its evaluation history?
          </p>
        </DrawerContent>
        <DrawerFooter>
          <Button variant="outline" onClick={() => setConfirmId(null)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              if (confirmId) onDelete(confirmId)
              setConfirmId(null)
            }}
          >
            Delete
          </Button>
        </DrawerFooter>
      </Drawer>
    </div>
  )
}

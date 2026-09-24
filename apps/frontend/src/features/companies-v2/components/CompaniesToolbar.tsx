'use client'

import { useMemo, useRef } from 'react'
import { DebouncedInput } from '@/shared/ui/debounced-input'
import { Button } from '@/shared/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/shared/ui/select'
import type { CompanyListItem } from '@/entities/company/types'
import { MagnifyingGlass, Buildings, PushPin, Funnel } from '@phosphor-icons/react'
import { ColumnsDropdown } from '@/shared/components/ColumnsDropdown'
import { cn } from '@/shared/lib/utils'
import { useFocusSearchShortcut } from '@/shared/hooks'

const STATUS_LABELS: Record<string, string> = {
  created: 'Created',
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  none: 'Not processed',
}

const COMPANY_TYPE_LABELS: Record<string, string> = {
  PRODUCT_COMPANY: 'Product',
  RECRUITING_AGENCY: 'Recruiting agency',
  STAFFING_COMPANY: 'Staffing',
  CONSULTING_COMPANY: 'Consulting',
  UNKNOWN: 'Unknown',
}

interface CompaniesToolbarProps {
  query: string
  onQueryChange: (value: string) => void
  filterIndustry: string
  onFilterIndustryChange: (value: string) => void
  filterCompanyType: string
  onFilterCompanyTypeChange: (value: string) => void
  filterStatus: string
  onFilterStatusChange: (value: string) => void
  filterPinned: boolean
  onFilterPinnedChange: (value: boolean) => void
  items: CompanyListItem[]
  activeFilterCount: number
  onClearFilters: () => void
  showRowNumberColumn?: boolean
  onToggleRowNumberColumn?: (value: boolean) => void
}

export function CompaniesToolbar({
  query, onQueryChange,
  filterIndustry, onFilterIndustryChange,
  filterCompanyType, onFilterCompanyTypeChange,
  filterStatus, onFilterStatusChange,
  filterPinned, onFilterPinnedChange,
  items, activeFilterCount, onClearFilters,
  showRowNumberColumn = false, onToggleRowNumberColumn,
}: CompaniesToolbarProps) {
  const searchRef = useRef<HTMLInputElement>(null)
  useFocusSearchShortcut(searchRef)

  const industries = useMemo(() => {
    const set = new Set<string>()
    items.forEach(c => {
      if (c.industry) set.add(c.industry)
    })
    return [...set].sort()
  }, [items])

  return (
    <div className="px-3 py-2 border-b border-border/40">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <DebouncedInput
            ref={searchRef}
            value={query}
            onValueChange={onQueryChange}
            placeholder="Search by name, industry, or location..."
            icon={<MagnifyingGlass className="w-3.5 h-3.5 text-muted-foreground" />}
            clearable
            clearLabel="Clear search"
            activeClassName="border-emerald-500/30"
            wrapperClassName="w-full"
            inputClassName="pl-8 h-7 text-xs"
            aria-label="Search companies"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Select value={filterIndustry} onValueChange={onFilterIndustryChange}>
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <Buildings className="w-3 h-3" />
              <span>{filterIndustry || 'Industry'}</span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              {industries.map(ind => (
                <SelectItem key={ind} value={ind}>{ind}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterCompanyType} onValueChange={onFilterCompanyTypeChange}>
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <Buildings className="w-3 h-3" />
              <span>{filterCompanyType ? COMPANY_TYPE_LABELS[filterCompanyType] ?? filterCompanyType : 'Type'}</span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              {Object.entries(COMPANY_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterStatus} onValueChange={onFilterStatusChange}>
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <Funnel className="w-3 h-3" />
              <span>{filterStatus ? STATUS_LABELS[filterStatus] ?? filterStatus : 'Status'}</span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              <SelectItem value="created">Created</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="none">Not processed</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="sm"
            className={cn('h-7 w-auto gap-1 text-2xs', filterPinned && 'text-primary')}
            onClick={() => onFilterPinnedChange(!filterPinned)}
            aria-label="Show pinned companies only"
            aria-pressed={filterPinned}
            title={filterPinned ? 'Showing pinned companies only' : 'Show pinned companies only'}
          >
            <PushPin className="w-3 h-3" weight={filterPinned ? 'fill' : 'regular'} />
            Pinned
          </Button>
          {onToggleRowNumberColumn && (
            <ColumnsDropdown
              options={[{ key: 'rowNumber', label: 'Row number', checked: showRowNumberColumn }]}
              onToggle={(key, checked) => {
                if (key === 'rowNumber') onToggleRowNumberColumn?.(checked)
              }}
            />
          )}
          {activeFilterCount > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-2xs text-emerald-500" onClick={onClearFilters}>
              Clear
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

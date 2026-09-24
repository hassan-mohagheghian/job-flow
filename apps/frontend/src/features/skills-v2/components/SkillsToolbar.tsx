'use client'

import { useRef } from 'react'
import { DebouncedInput } from '@/shared/ui/debounced-input'
import { Button } from '@/shared/ui/button'
import { MagnifyingGlass, FunnelSimple, PushPin, GitMerge, X } from '@phosphor-icons/react'
import { ColumnsDropdown } from '@/shared/components/ColumnsDropdown'
import { cn } from '@/shared/lib/utils'
import { CategoryMultiSelect } from './CategoryMultiSelect'
import { useFocusSearchShortcut } from '@/shared/hooks'

interface SkillsToolbarProps {
  query: string
  onQueryChange: (value: string) => void
  filterCategories: string[]
  onFilterCategoriesChange: (value: string[]) => void
  categoryOptions: string[]
  filterPinned?: boolean
  onFilterPinnedChange?: (value: boolean) => void
  activeFilterCount: number
  onClearFilters: () => void
  showSelectColumn?: boolean
  onToggleSelectColumn?: (value: boolean) => void
  showRowNumberColumn?: boolean
  onToggleRowNumberColumn?: (value: boolean) => void
  selectedCount?: number
  onMergeSelected?: () => void
  onClearSelection?: () => void
  mergePending?: boolean
}

export function SkillsToolbar({
  query,
  onQueryChange,
  filterCategories,
  onFilterCategoriesChange,
  categoryOptions,
  filterPinned = false,
  onFilterPinnedChange,
  activeFilterCount,
  onClearFilters,
  showSelectColumn = false,
  onToggleSelectColumn,
  showRowNumberColumn = false,
  onToggleRowNumberColumn,
  selectedCount = 0,
  onMergeSelected,
  onClearSelection,
  mergePending = false,
}: SkillsToolbarProps) {
  const searchRef = useRef<HTMLInputElement>(null)
  useFocusSearchShortcut(searchRef)

  return (
    <div className="px-3 py-2 border-b border-border/40">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <DebouncedInput
            ref={searchRef}
            value={query}
            onValueChange={onQueryChange}
            placeholder="Search by name, role, path, or alias..."
            icon={<MagnifyingGlass className="w-3.5 h-3.5 text-muted-foreground" />}
            clearable
            clearLabel="Clear search"
            activeClassName="border-emerald-500/30"
            wrapperClassName="w-full"
            inputClassName="pl-8 h-7 text-xs"
            aria-label="Search skills"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <CategoryMultiSelect
            value={filterCategories}
            onChange={onFilterCategoriesChange}
            options={categoryOptions}
            placeholder="Category"
            icon={<FunnelSimple className="w-3 h-3" />}
            align="end"
          />
          {onFilterPinnedChange && (
            <Button
              variant="ghost"
              size="sm"
              className={cn('h-7 w-auto gap-1 text-2xs', filterPinned && 'text-primary')}
              onClick={() => onFilterPinnedChange(!filterPinned)}
              aria-label="Show pinned skills only"
              aria-pressed={filterPinned}
              title={filterPinned ? 'Showing pinned skills only' : 'Show pinned skills only'}
            >
              <PushPin className="w-3 h-3" weight={filterPinned ? 'fill' : 'regular'} />
              Pinned
            </Button>
          )}
          {(onToggleSelectColumn || onToggleRowNumberColumn) && (
            <ColumnsDropdown
              options={[
                ...(onToggleRowNumberColumn ? [{ key: 'rowNumber', label: 'Row number', checked: showRowNumberColumn }] : []),
                ...(onToggleSelectColumn ? [{ key: 'select', label: 'Select', checked: showSelectColumn }] : []),
              ]}
              onToggle={(key, checked) => {
                if (key === 'rowNumber') onToggleRowNumberColumn?.(checked)
                else onToggleSelectColumn?.(checked)
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
      {selectedCount > 0 && (
        <div className="flex items-center gap-2 mt-2">
          <span className="text-2xs text-muted-foreground">
            {selectedCount} selected
          </span>
          <Button variant="default" size="sm" className="h-7 text-2xs gap-1" onClick={onMergeSelected} disabled={mergePending}>
            <GitMerge className="w-3 h-3" />
            Merge {selectedCount} into...
          </Button>
          <Button variant="ghost" size="sm" className="h-7 text-2xs gap-1" onClick={onClearSelection}>
            <X className="w-3 h-3" />
            Clear
          </Button>
        </div>
      )}
    </div>
  )
}

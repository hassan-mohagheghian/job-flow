"use client";

import { useRef } from "react";
import { DebouncedInput } from "@/shared/ui/debounced-input";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/shared/ui/select";
import { MultiSelectFilter } from "./MultiSelectFilter";
import type {
  ProcessingStatusFilter,
  RecommendationFilter,
  TrackingStatusFilter,
  CreatedDateFilter,
} from "@/entities/job/types";
import {
  MagnifyingGlass,
  MapPin,
  Funnel,
  PushPin,
} from "@phosphor-icons/react";
import { cn } from "@/shared/lib/utils";
import { ColumnsDropdown } from "@/shared/components/ColumnsDropdown";
import { useFocusSearchShortcut } from "@/shared/hooks";

const STATUS_FILTER_LABELS: Record<string, string> = {
  created: "Created",
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  none: "Not processed",
};

const RECOMMENDATION_LABELS: Record<RecommendationFilter, string> = {
  apply: "Apply",
  consider: "Consider",
  skip: "Skip",
};

const RECOMMENDATION_OPTIONS = Object.entries(RECOMMENDATION_LABELS).map(
  ([value, label]) => ({ value, label }),
);

const TRACKING_FILTER_LABELS: Record<TrackingStatusFilter, string> = {
  not_applied: "Not Applied",
  seen: "Seen",
  preparing: "Preparing",
  ready_to_apply: "Ready to Apply",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  expired: "Expired",
};

const TRACKING_OPTIONS = Object.entries(TRACKING_FILTER_LABELS).map(
  ([value, label]) => ({ value, label }),
);

const CREATED_DATE_LABELS: Record<string, string> = {
  today: "Today",
  yesterday: "Yesterday",
  week: "Last Week",
  month: "Last Month",
};

interface JobsToolbarProps {
  query: string;
  onQueryChange: (value: string) => void;
  filterProcessingStatus: ProcessingStatusFilter;
  onFilterProcessingStatusChange: (value: ProcessingStatusFilter) => void;
  filterLocation: string;
  onFilterLocationChange: (value: string) => void;
  filterRemote: boolean | "";
  onFilterRemoteChange: (value: boolean | "") => void;
  filterVisa: boolean | "";
  onFilterVisaChange: (value: boolean | "") => void;
  filterPinned: boolean;
  onFilterPinnedChange: (value: boolean) => void;
  filterRecommendation: RecommendationFilter[];
  onFilterRecommendationChange: (value: RecommendationFilter[]) => void;
  filterTrackingStatus: TrackingStatusFilter[];
  onFilterTrackingStatusChange: (value: TrackingStatusFilter[]) => void;
  filterCreatedDate: CreatedDateFilter;
  onFilterCreatedDateChange: (value: CreatedDateFilter) => void;
  activeFilterCount: number;
  onClearFilters: () => void;
  showPinnedColumn?: boolean;
  onTogglePinnedColumn?: (value: boolean) => void;
  showRowNumberColumn?: boolean;
  onToggleRowNumberColumn?: (value: boolean) => void;
}

export function JobsToolbar({
  query,
  onQueryChange,
  filterProcessingStatus,
  onFilterProcessingStatusChange,
  filterLocation,
  onFilterLocationChange,
  filterRemote,
  onFilterRemoteChange,
  filterVisa,
  onFilterVisaChange,
  filterPinned,
  onFilterPinnedChange,
  filterRecommendation,
  onFilterRecommendationChange,
  filterTrackingStatus,
  onFilterTrackingStatusChange,
  filterCreatedDate,
  onFilterCreatedDateChange,
  activeFilterCount,
  onClearFilters,
  showPinnedColumn = true,
  onTogglePinnedColumn,
  showRowNumberColumn = false,
  onToggleRowNumberColumn,
}: JobsToolbarProps) {
  const searchRef = useRef<HTMLInputElement>(null);
  useFocusSearchShortcut(searchRef);

  return (
    <div className="px-3 py-2 border-b border-border/40">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <DebouncedInput
            ref={searchRef}
            value={query}
            onValueChange={onQueryChange}
            placeholder="Search by title, company, or keyword..."
            icon={
              <MagnifyingGlass className="w-3.5 h-3.5 text-muted-foreground" />
            }
            clearable
            clearLabel="Clear search"
            activeClassName="border-emerald-500/30"
            wrapperClassName="w-full"
            inputClassName="pl-8 h-7 text-xs"
            aria-label="Search jobs"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <div className="relative w-36">
            <DebouncedInput
              value={filterLocation}
              onValueChange={onFilterLocationChange}
              placeholder="Location..."
              icon={<MapPin className="w-3 h-3 text-muted-foreground" />}
              clearable
              clearLabel="Clear location filter"
              activeClassName="border-emerald-500/30"
              wrapperClassName="w-full"
              inputClassName="pl-6 h-7 text-2xs"
              aria-label="Filter by location"
            />
          </div>
          <Select
            value={filterProcessingStatus}
            onValueChange={(v) =>
              onFilterProcessingStatusChange(v as ProcessingStatusFilter)
            }
          >
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <Funnel className="w-3 h-3" />
              <span>
                {filterProcessingStatus
                  ? (STATUS_FILTER_LABELS[filterProcessingStatus] ??
                    filterProcessingStatus)
                  : "Status"}
              </span>
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
          <Select
            value={filterRemote !== "" ? String(filterRemote) : ""}
            onValueChange={(v) =>
              onFilterRemoteChange(v === "" ? "" : v === "true")
            }
          >
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <span>
                {filterRemote !== ""
                  ? filterRemote
                    ? "Remote"
                    : "On-site"
                  : "Remote"}
              </span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              <SelectItem value="true">Remote</SelectItem>
              <SelectItem value="false">On-site</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={filterVisa !== "" ? String(filterVisa) : ""}
            onValueChange={(v) =>
              onFilterVisaChange(v === "" ? "" : v === "true")
            }
          >
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <span>
                {filterVisa !== "" ? (filterVisa ? "Visa" : "No Visa") : "Visa"}
              </span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              <SelectItem value="true">Visa</SelectItem>
              <SelectItem value="false">No Visa</SelectItem>
            </SelectContent>
          </Select>
          <MultiSelectFilter
            label="Recommendation"
            options={RECOMMENDATION_OPTIONS}
            selected={filterRecommendation}
            onChange={onFilterRecommendationChange}
          />
          <MultiSelectFilter
            label="Tracking"
            options={TRACKING_OPTIONS}
            selected={filterTrackingStatus}
            onChange={onFilterTrackingStatusChange}
          />
          <Select
            value={filterCreatedDate}
            onValueChange={(v) =>
              onFilterCreatedDateChange(v as CreatedDateFilter)
            }
          >
            <SelectTrigger className="h-7 w-auto text-2xs gap-1 text-primary">
              <span>
                {filterCreatedDate
                  ? (CREATED_DATE_LABELS[filterCreatedDate] ??
                    filterCreatedDate)
                  : "Date"}
              </span>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value="">All</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="yesterday">Yesterday</SelectItem>
              <SelectItem value="week">Last Week</SelectItem>
              <SelectItem value="month">Last Month</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              "h-7 w-auto gap-1 text-2xs",
              filterPinned && "text-primary",
            )}
            onClick={() => onFilterPinnedChange(!filterPinned)}
            aria-label="Show pinned only"
            aria-pressed={filterPinned}
            title={filterPinned ? "Showing pinned only" : "Show pinned only"}
          >
            <PushPin
              className="w-3 h-3"
              weight={filterPinned ? "fill" : "regular"}
            />
            Pinned
          </Button>
          {(onTogglePinnedColumn || onToggleRowNumberColumn) && (
            <ColumnsDropdown
              options={[
                ...(onToggleRowNumberColumn
                  ? [
                      {
                        key: "rowNumber",
                        label: "Row number",
                        checked: showRowNumberColumn,
                      },
                    ]
                  : []),
                ...(onTogglePinnedColumn
                  ? [
                      {
                        key: "pinned",
                        label: "Pinned",
                        checked: showPinnedColumn,
                      },
                    ]
                  : []),
              ]}
              onToggle={(key, checked) => {
                if (key === "rowNumber") onToggleRowNumberColumn?.(checked);
                else onTogglePinnedColumn(checked);
              }}
            />
          )}
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-2xs text-emerald-500"
              onClick={onClearFilters}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

'use client'

import { cn } from '@/shared/lib/utils'
import type { OpportunityStatus } from '@/entities/opportunity/types'

const STATUS_STYLES: Record<OpportunityStatus, string> = {
  new: 'bg-muted text-muted-foreground',
  extracted: 'bg-blue-500/10 text-blue-500',
  enriching: 'bg-cyan-500/10 text-cyan-500',
  needs_info: 'bg-orange-500/10 text-orange-500',
  evaluated: 'bg-violet-500/10 text-violet-500',
  ready_to_apply: 'bg-green-500/10 text-green-600',
  applied: 'bg-green-600/10 text-green-700',
  replied: 'bg-teal-500/10 text-teal-600',
  interview: 'bg-indigo-500/10 text-indigo-500',
  rejected: 'bg-red-500/10 text-red-500',
  closed: 'bg-muted text-muted-foreground',
}

const STATUS_LABELS: Record<OpportunityStatus, string> = {
  new: 'New',
  extracted: 'Extracted',
  enriching: 'Enriching',
  needs_info: 'Needs Info',
  evaluated: 'Evaluated',
  ready_to_apply: 'Ready to Apply',
  applied: 'Applied',
  replied: 'Replied',
  interview: 'Interview',
  rejected: 'Rejected',
  closed: 'Closed',
}

export function OpportunityStatusBadge({ status }: { status: OpportunityStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        STATUS_STYLES[status] ?? STATUS_STYLES.new,
      )}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

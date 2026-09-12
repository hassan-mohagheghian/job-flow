import { cn } from '@/shared/lib/utils'
import type { ApplicationStatus } from '@/entities/application/types'

interface ApplicationStatusBadgeProps {
  status: ApplicationStatus
  className?: string
}

const statusConfig: Record<ApplicationStatus, { color: string; label: string }> = {
  seen: { color: 'bg-slate-500/15 text-slate-500 border-slate-500/20', label: 'Seen' },
  preparing: { color: 'bg-amber-500/15 text-amber-500 border-amber-500/20', label: 'Preparing' },
  ready_to_apply: { color: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/20', label: 'Ready to Apply' },
  applied: { color: 'bg-green-500/15 text-green-500 border-green-500/20', label: 'Applied' },
  interview: { color: 'bg-cyan-500/15 text-cyan-500 border-cyan-500/20', label: 'Interview' },
  offer: { color: 'bg-purple-500/15 text-purple-500 border-purple-500/20', label: 'Offer' },
  accepted: { color: 'bg-emerald-600/15 text-emerald-600 border-emerald-600/20', label: 'Accepted' },
  rejected: { color: 'bg-red-500/15 text-red-500 border-red-500/20', label: 'Rejected' },
  withdrawn: { color: 'bg-gray-500/15 text-gray-500 border-gray-500/20', label: 'Withdrawn' },
  expired: { color: 'bg-orange-500/15 text-orange-500 border-orange-500/20', label: 'Expired' },
}

export function ApplicationStatusBadge({ status, className }: ApplicationStatusBadgeProps) {
  const config = statusConfig[status] || {
    color: 'bg-gray-500/15 text-gray-500 border-gray-500/20',
    label: status,
  }
  return (
    <span className={cn(
      'inline-flex items-center px-1.5 py-0.5 rounded text-2xs font-medium border capitalize',
      config.color,
      className
    )}>
      {config.label}
    </span>
  )
}

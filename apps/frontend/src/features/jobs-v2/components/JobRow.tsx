import type { JobListItem } from '@/entities/job/types'
import type { ProcessingStatus as PStatus } from '@/entities/job/types'
import { ScoreBadge } from './ScoreBadge'
import { ProcessingStatus } from './ProcessingStatus'
import { JobActions } from './JobActions'
import { PinButton } from '@/shared/components/PinButton'
import { cn } from '@/shared/lib/utils'
import { RecommendationBadge } from './RecommendationBadge'
import { TrackingBadge } from './TrackingBadge'
import DateTime from '@/shared/components/DateTime'
import { GradeBadge } from '@/shared/components/GradeBadge'
import { RankBadge } from '@/shared/components/RankBadge'
import { gradeForScore } from '@/shared/lib/grade'
import { ClampText } from './ClampText'

interface JobRowProps {
  job: JobListItem
  onProcessV2: (id: string) => void
  onViewDetails: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onTogglePinned: (id: string, pinned: boolean) => void
  onRetry?: (id: string) => void
  onCancel?: (id: string) => void
  onApplication?: (id: string) => void
  showPinnedColumn?: boolean
  showRowNumberColumn?: boolean
  rowNumber?: number
  gridTemplate?: string
}

export function JobRow({
  job, onProcessV2, onViewDetails, onEdit, onDelete, onTogglePinned, onRetry, onCancel, onApplication,
  showPinnedColumn = true, showRowNumberColumn = false, rowNumber, gridTemplate,
}: JobRowProps) {
  const processingStatus: PStatus | null = job.latest_processing_execution?.status ?? null

  const allTags: { label: string; color: string }[] = [
    ...(job.tags ?? []).map(t => ({ label: t, color: 'bg-muted text-muted-foreground border-border' })),
    ...(job.dismissed ? [{ label: 'Dismissed', color: 'bg-red-500/10 text-red-500 border-red-500/20' }] : []),
    ...(job.visa_sponsorship ? [{ label: 'Visa', color: 'bg-blue-500/10 text-blue-500 border-blue-500/20' }] : []),
    ...(job.easy_apply ? [{ label: 'Easy Apply', color: 'bg-sky-500/10 text-sky-500 border-sky-500/20' }] : []),
  ]

  return (
    <div
      className="group relative grid border-b border-border/40 hover:bg-muted/50 hover:ring-1 hover:ring-inset hover:ring-border/60 focus-within:bg-muted/50 cursor-pointer transition-colors items-start"
      style={gridTemplate ? { gridTemplateColumns: gridTemplate } : undefined}
      onClick={() => onViewDetails(job.id)}
    >
      {showRowNumberColumn && (
        <div className="py-2 px-3 flex items-center justify-center">
          <span className="text-2xs text-muted-foreground tabular-nums">{rowNumber ?? ''}</span>
        </div>
      )}
      {showPinnedColumn && (
        <div className="py-2 px-2 flex items-center justify-center" onClick={e => e.stopPropagation()}>
          <PinButton pinned={job.pinned} onToggle={() => onTogglePinned(job.id, !job.pinned)} entityLabel="job" />
        </div>
      )}
      <div className="py-2 px-3 flex items-center">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-medium text-foreground truncate">
            {job.title || 'Untitled'}
          </span>
        </div>
      </div>
      <div className="py-2 px-3 flex items-center">
        <ClampText text={job.company_name || 'Unknown'} className="text-xs text-muted-foreground" />
      </div>
      <div className="py-2 px-3 flex items-center">
        <div className="flex items-center gap-1.5 min-w-0">
          <ClampText text={job.location || 'Unknown'} className="text-xs text-muted-foreground" />
          {job.remote && (
            <span className="text-2xs px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 whitespace-nowrap">
              Remote
            </span>
          )}
        </div>
      </div>
      <div className="py-2 px-3 flex items-center">
        <div className="flex items-center gap-2 whitespace-nowrap min-w-0 overflow-hidden">
          <GradeBadge grade={gradeForScore(job.scores?.overall ?? null)} className="w-7 h-5 text-2xs" />
          <RankBadge rank={job.rank ?? null} variant="inline" />
          <ScoreBadge label="O" value={job.scores?.overall ?? null} />
          <ScoreBadge label="S" value={job.scores?.success ?? null} />
          <ScoreBadge label="F" value={job.scores?.fit ?? null} />
        </div>
      </div>
      <div className="py-2 px-3 flex items-center min-w-0 overflow-hidden">
        <RecommendationBadge recommendation={job.recommendation} />
      </div>
      <div className="py-2 px-3 flex items-start">
        <div className="flex flex-wrap items-center gap-1 min-w-0">
          {allTags.map((tag, i) => (
            <span
              key={`${tag.label}-${i}`}
              className={cn(
                'text-2xs px-1 py-0.5 rounded border whitespace-nowrap font-medium',
                tag.color
              )}
            >
              {tag.label}
            </span>
          ))}
        </div>
      </div>
      <div className="py-2 px-3 flex items-center">
        <TrackingBadge status={job.tracking_status} />
      </div>
      <div className="py-2 px-3 flex items-center">
        <ProcessingStatus status={processingStatus} />
      </div>
      <div className="py-2 px-3 flex items-center">
        <DateTime value={job.updated_at} format="relative" className="text-2xs text-muted-foreground" />
      </div>
      <div className="py-2 px-3 flex items-center">
        <DateTime value={job.created_at} format="relative" className="text-2xs text-muted-foreground" />
      </div>
      <div className="absolute inset-y-0 right-1 flex items-center opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
        <div className="flex items-center bg-card ring-1 ring-border rounded-md shadow-sm px-1">
          <JobActions
            processingStatus={processingStatus}
            onProcessV2={() => onProcessV2(job.id)}
            onViewDetails={() => onViewDetails(job.id)}
            onEdit={() => onEdit(job.id)}
            onDelete={() => onDelete(job.id)}
            onRetry={() => onRetry?.(job.id)}
            onCancel={() => onCancel?.(job.id)}
            onApplication={onApplication ? () => onApplication(job.id) : undefined}
          />
        </div>
      </div>
    </div>
  )
}

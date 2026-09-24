import type { CompanyListItem } from '@/entities/company/types'
import { isRecruiterCompany, formatCompanyTypeShort, companyTypeRowClasses } from '@/entities/company/lib'
import { ScoreBadge } from '@/features/jobs-v2/components/ScoreBadge'
import { StatusBadge } from '@/features/jobs-v2/components/StatusBadge'
import type { ProcessingStatus } from '@/entities/job/types'
import { Badge } from '@/shared/ui/badge'
import { formatCityLocation } from '@/shared/lib/formatLocation'
import DateTime from '@/shared/components/DateTime'
import { GradeBadge } from '@/shared/components/GradeBadge'
import { gradeForScore } from '@/shared/lib/grade'
import { cn } from '@/shared/lib/utils'
import { buildCompanyGridTemplate } from './companiesColumns'
import { CompanyActions } from './CompanyActions'

interface CompanyRowProps {
  company: CompanyListItem
  onViewDetails: (id: string) => void
  onReprocess: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  showRowNumberColumn?: boolean
  rowNumber?: number
}

export function CompanyRow({
  company, onViewDetails, onReprocess, onEdit, onDelete,
  showRowNumberColumn = false, rowNumber,
}: CompanyRowProps) {
  const grade = company.scores?.overall_grade ?? (company.scores?.overall != null ? gradeForScore(company.scores.overall) : null)
  const processingStatus = (company.processing?.status ?? null) as ProcessingStatus | null
  const recruiter = isRecruiterCompany(company)
  const typeTint = companyTypeRowClasses(company.company_type) || (recruiter ? 'bg-purple-500/5 hover:bg-purple-500/10 focus-within:bg-purple-500/10' : '')
  const listedJobs = recruiter ? company.recruiter_job_count : company.job_count
  const listedLabel = recruiter
    ? `${listedJobs} ${listedJobs === 1 ? 'job' : 'jobs'} listed for clients`
    : `${listedJobs} ${listedJobs === 1 ? 'job' : 'jobs'}`

  return (
    <div
      className={cn(
        "group relative grid border-b border-border/40 hover:bg-muted/50 hover:ring-1 hover:ring-inset hover:ring-border/60 focus-within:bg-muted/50 cursor-pointer transition-colors items-center",
        typeTint
      )}
      style={{ gridTemplateColumns: buildCompanyGridTemplate(showRowNumberColumn) }}
      onClick={() => onViewDetails(company.id)}
      data-recruiter={recruiter ? "true" : "false"}
    >
      {showRowNumberColumn && (
        <div className="py-2 px-3 flex items-center justify-center">
          <span className="text-2xs text-muted-foreground tabular-nums">{rowNumber ?? ''}</span>
        </div>
      )}
      <div className="py-2 px-3 flex items-center">
        <div className="flex items-center gap-2 min-w-0">
          {company.logo_url && (
            <img src={company.logo_url} alt="" className="w-4 h-4 rounded shrink-0" />
          )}
          <span className="text-xs font-medium text-foreground truncate">{company.name}</span>
          {company.is_alias && (
            <Badge variant="secondary" className="shrink-0 h-4 px-1.5 text-2xs text-muted-foreground">
              alias
            </Badge>
          )}
        </div>
      </div>
      <div className="py-2 px-3 flex items-center">
        <span className="text-xs text-muted-foreground truncate block">{company.industry || 'Unknown'}</span>
      </div>
      <div className="py-2 px-3 flex items-center">
        <Badge variant="secondary" className="text-2xs truncate max-w-full">
          {formatCompanyTypeShort(company.company_type)}
        </Badge>
      </div>
      <div className="py-2 px-3 flex items-center">
        <span className="text-xs text-muted-foreground truncate block">
          {formatCityLocation(company.city, company.country) || 'Unknown'}
        </span>
      </div>
      <div className="py-2 px-3 flex items-center">
        <span className="text-xs text-muted-foreground truncate block">{company.company_size || '—'}</span>
      </div>
      <div className="py-2 px-3 flex items-center">
        <span className="text-xs text-muted-foreground" title={listedJobs > 0 ? listedLabel : undefined}>
          {listedJobs > 0 ? listedJobs : '—'}
        </span>
      </div>
      <div className="py-2 px-3 flex items-center">
        <div className="flex items-center gap-2 whitespace-nowrap">
          <GradeBadge grade={grade} className="w-7 h-5 text-2xs" />
          <ScoreBadge label="O" value={company.scores?.overall ?? null} />
          <ScoreBadge label="S" value={company.scores?.success ?? null} />
          <ScoreBadge label="F" value={company.scores?.fit ?? null} />
        </div>
      </div>
      <div className="py-2 px-3 flex items-center">
        <StatusBadge status={processingStatus} />
      </div>
      <div className="py-2 px-3 flex items-center">
        <DateTime value={company.updated_at} format="relative" className="text-2xs text-muted-foreground" />
      </div>
      <div className="py-2 px-3 flex items-center">
        <DateTime value={company.created_at} format="relative" className="text-2xs text-muted-foreground" />
      </div>
      <div className="absolute inset-y-0 right-1 flex items-center opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
        <div className="flex items-center bg-card ring-1 ring-border rounded-md shadow-sm px-1">
          <CompanyActions
            onViewDetails={() => onViewDetails(company.id)}
            onReprocess={() => onReprocess(company.id)}
            onEdit={() => onEdit(company.id)}
            onDelete={() => onDelete(company.id)}
          />
        </div>
      </div>
    </div>
  )
}

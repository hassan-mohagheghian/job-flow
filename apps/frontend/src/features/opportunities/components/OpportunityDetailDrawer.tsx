'use client'

import { useState } from 'react'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader } from '@/shared/components/Drawer'
import {
  useAddOpportunityNote,
  useDeleteOpportunity,
  useDeleteOpportunityNote,
  useOpportunityDetailQuery,
  useProcessOpportunity,
  useUpdateOpportunityStatus,
} from '@/entities/opportunity/hooks'
import type { OpportunityStatus } from '@/entities/opportunity/types'
import { OpportunityStatusBadge } from './OpportunityStatusBadge'

interface OpportunityDetailDrawerProps {
  opportunityId: string | null
  onClose: () => void
}

const STATUS_OPTIONS: OpportunityStatus[] = [
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border p-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        {title}
      </h3>
      {children}
    </section>
  )
}

export function OpportunityDetailDrawer({ opportunityId, onClose }: OpportunityDetailDrawerProps) {
  const detailQuery = useOpportunityDetailQuery(opportunityId)
  const processMutation = useProcessOpportunity()
  const statusMutation = useUpdateOpportunityStatus()
  const deleteMutation = useDeleteOpportunity()
  const addNoteMutation = useAddOpportunityNote()
  const deleteNoteMutation = useDeleteOpportunityNote()
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')

  const opportunity = detailQuery.data

  const handleAddNote = () => {
    if (!opportunityId || !noteContent.trim() || addNoteMutation.isPending) return
    addNoteMutation.mutate(
      {
        id: opportunityId,
        data: { title: noteTitle.trim() || null, content: noteContent.trim() },
      },
      {
        onSuccess: () => {
          setNoteTitle('')
          setNoteContent('')
        },
      },
    )
  }

  return (
    <Drawer open={opportunityId !== null} onOpenChange={(open) => !open && onClose()}>
      <DrawerHeader title={opportunity?.title ?? 'Opportunity'} onClose={onClose} />
      <DrawerContent>
        {detailQuery.isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        ) : detailQuery.isError || !opportunity ? (
          <p className="text-sm text-muted-foreground">Failed to load the opportunity.</p>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <OpportunityStatusBadge status={opportunity.status} />
              <span className="text-xs text-muted-foreground capitalize">{opportunity.source}</span>
              {opportunity.company_name && (
                <span className="text-xs text-muted-foreground">{opportunity.company_name}</span>
              )}
              <span className="flex-1" />
              <Button
                size="sm"
                onClick={() => opportunityId && processMutation.mutate({ id: opportunityId })}
                disabled={processMutation.isPending}
              >
                {processMutation.isPending ? 'Processing…' : 'Process'}
              </Button>
            </div>

            <Section title="Score">
              {opportunity.overall_score != null ? (
                <div>
                  <div className="flex items-center gap-4">
                    <span className="text-2xl font-bold">{opportunity.overall_score}</span>
                    <span className="text-xs text-muted-foreground">
                      Fit {opportunity.fit_score ?? '—'} · Success {opportunity.success_score ?? '—'} ·{' '}
                      {opportunity.recommendation ?? '—'}
                    </span>
                  </div>
                  {(opportunity.evaluation?.concerns as string[] | undefined)?.length ? (
                    <ul className="mt-2 text-xs space-y-1">
                  {(opportunity.evaluation.concerns as string[]).map((c) => (
                    <li key={c}>
                      <span aria-hidden="true">• </span>
                      {c}
                    </li>
                  ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Evaluation pending
                  {opportunity.missing_information?.length
                    ? `: ${(opportunity.missing_information as string[]).join(', ')}`
                    : ''}
                </p>
              )}
            </Section>

            {opportunity.next_action && (
              <Section title="Next">
                <p className="text-sm font-medium">{opportunity.next_action}</p>
                {opportunity.application_path?.label && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {`Path: ${String(opportunity.application_path.label)}${
                      opportunity.application_path?.url
                        ? ` — ${String(opportunity.application_path.url)}`
                        : ''
                    }`}
                  </p>
                )}
              </Section>
            )}

            <Section title="Original Message">
              <p className="text-xs whitespace-pre-wrap break-words">{opportunity.raw_content}</p>
              <p className="text-2xs text-muted-foreground mt-2">
                {[opportunity.sender, opportunity.sender_email, opportunity.subject]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </Section>

            {Object.keys(opportunity.extracted ?? {}).length > 0 && (
              <Section title="Extracted">
                <dl className="text-xs space-y-1">
                  {opportunity.extracted.role_title && (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground w-20 shrink-0">Role</dt>
                      <dd>{String(opportunity.extracted.role_title)}</dd>
                    </div>
                  )}
                  {opportunity.extracted?.company?.name && (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground w-20 shrink-0">Company</dt>
                      <dd>
                        {String(opportunity.extracted.company.name)}
                        {opportunity.extracted.company.state &&
                          opportunity.extracted.company.state !== 'known' && (
                            <span className="text-muted-foreground">
                              {' '}
                              ({String(opportunity.extracted.company.state).replaceAll('_', ' ')})
                            </span>
                          )}
                      </dd>
                    </div>
                  )}
                  {opportunity.extracted?.location?.value && (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground w-20 shrink-0">Location</dt>
                      <dd>{String(opportunity.extracted.location.value)}</dd>
                    </div>
                  )}
                  {(opportunity.extracted?.job_urls as string[] | undefined)?.length ? (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground w-20 shrink-0">Links</dt>
                      <dd className="break-all">
                        {(opportunity.extracted.job_urls as string[]).join(', ')}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              </Section>
            )}

            {(opportunity.job_id || opportunity.company_id) && (
              <Section title="Links">
                <div className="text-xs space-y-1">
                  {opportunity.job_id && <p>Job: {opportunity.job_title ?? opportunity.job_id}</p>}
                  {opportunity.company_id && (
                    <p>Company: {opportunity.company_name ?? opportunity.company_id}</p>
                  )}
                </div>
              </Section>
            )}

              {(opportunity.evaluation?.missing_requirements as string[] | undefined)?.length ? (
              <Section title="Missing">
                <ul className="text-xs space-y-1">
                  {(opportunity.evaluation.missing_requirements as string[]).map((m) => (
                    <li key={m}>
                      <span aria-hidden="true">• </span>
                      {m}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            <Section title="Follow-ups">
              {opportunity.notes?.length ? (
                <ul className="space-y-2">
                  {opportunity.notes.map((note) => (
                    <li key={note.id} className="rounded-md bg-muted/50 p-2">
                      <div className="flex items-start gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold truncate">
                            {note.title || 'Note'}
                          </p>
                          <p className="text-2xs text-muted-foreground">
                            {[note.author, note.created_at].filter(Boolean).join(' · ')}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Delete note ${note.title || note.id}`}
                          disabled={deleteNoteMutation.isPending}
                          onClick={() =>
                            opportunityId &&
                            deleteNoteMutation.mutate({ id: opportunityId, noteId: note.id })
                          }
                        >
                          Delete
                        </Button>
                      </div>
                      <p className="text-xs whitespace-pre-wrap break-words mt-1">{note.content}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No follow-ups yet. Save recruiter replies and new details here for reassessment.
                </p>
              )}
              <div className="space-y-2 mt-2">
                <Input
                  aria-label="Note title"
                  placeholder="Title (e.g. Recruiter replied)"
                  value={noteTitle}
                  onChange={(e) => setNoteTitle(e.target.value)}
                />
                <Textarea
                  aria-label="New follow-up note"
                  placeholder="Paste the follow-up message or new details…"
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  rows={3}
                />
                <Button
                  size="sm"
                  disabled={!noteContent.trim() || addNoteMutation.isPending}
                  onClick={handleAddNote}
                >
                  {addNoteMutation.isPending ? 'Adding…' : 'Add follow-up'}
                </Button>
              </div>
            </Section>

            {opportunity.evaluations?.length ? (
              <Section title="History">
                <ul className="text-xs space-y-1">
                  {opportunity.evaluations.map((e) => (
                    <li key={e.id}>
                      {`${e.id} · ${e.status.replaceAll('_', ' ')} · ${e.overall_score ?? '—'}`}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}
          </div>
        )}
      </DrawerContent>
      <DrawerFooter>
        <label className="flex items-center gap-2 text-xs">
          Status
          <select
            aria-label="Status"
            value={opportunity?.status ?? 'new'}
            disabled={!opportunity}
            onChange={(e) =>
              opportunityId &&
              statusMutation.mutate({ id: opportunityId, status: e.target.value as OpportunityStatus })
            }
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        </label>
        <span className="flex-1" />
        <Button
          variant="destructive"
          size="sm"
          disabled={!opportunityId || deleteMutation.isPending}
          onClick={() =>
            opportunityId &&
            deleteMutation.mutate(opportunityId, {
              onSuccess: () => onClose(),
            })
          }
        >
          Delete opportunity
        </Button>
      </DrawerFooter>
    </Drawer>
  )
}

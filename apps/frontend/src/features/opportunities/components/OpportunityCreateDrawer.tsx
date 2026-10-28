'use client'

import { useEffect, useState } from 'react'
import { Plus, X } from '@phosphor-icons/react'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader } from '@/shared/components/Drawer'
import { DatePicker } from '@/shared/components/DatePicker'
import type {
  CreateOpportunityLinkRequest,
  CreateOpportunityNoteRequest,
  CreateOpportunityRequest,
  OpportunitySource,
} from '@/entities/opportunity/types'

interface OpportunityCreateDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateOpportunityRequest) => void
  submitting?: boolean
  error?: string | null
}

const SOURCE_OPTIONS: OpportunitySource[] = ['manual', 'gmail', 'linkedin']

const LINK_TITLE_PRESETS = ['LinkedIn', 'Website', 'Careers', 'GitHub'] as const

export function OpportunityCreateDrawer({
  open,
  onOpenChange,
  onSubmit,
  submitting = false,
  error = null,
}: OpportunityCreateDrawerProps) {
  const [source, setSource] = useState<OpportunitySource>('manual')
  const [sender, setSender] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [subject, setSubject] = useState('')
  const [receivedAt, setReceivedAt] = useState('')
  const [rawContent, setRawContent] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [notes, setNotes] = useState<CreateOpportunityNoteRequest[]>([])
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [links, setLinks] = useState<CreateOpportunityLinkRequest[]>([])
  const [linkUrl, setLinkUrl] = useState('')
  const [linkTitle, setLinkTitle] = useState('')

  useEffect(() => {
    if (!open) {
      setSource('manual')
      setSender('')
      setSenderEmail('')
      setSubject('')
      setReceivedAt('')
      setRawContent('')
      setBaseUrl('')
      setNotes([])
      setNoteTitle('')
      setNoteContent('')
      setLinks([])
      setLinkUrl('')
      setLinkTitle('')
    }
  }, [open])

  const handleAddNote = () => {
    if (!noteContent.trim()) return
    setNotes((items) => [
      ...items,
      { title: noteTitle.trim() || null, content: noteContent.trim() },
    ])
    setNoteTitle('')
    setNoteContent('')
  }

  const handleAddLink = () => {
    if (!linkUrl.trim()) return
    let url = linkUrl.trim()
    if (!url.startsWith('http')) url = 'https://' + url
    setLinks((items) => [...items, { title: linkTitle.trim() || null, url }])
    setLinkUrl('')
    setLinkTitle('')
  }

  const handleSubmit = () => {
    const normalizedBaseUrl = baseUrl.trim().startsWith('http')
      ? baseUrl.trim()
      : baseUrl.trim()
        ? 'https://' + baseUrl.trim()
        : null
    onSubmit({
      source,
      sender: sender.trim() || null,
      sender_email: senderEmail.trim() || null,
      subject: subject.trim() || null,
      received_at: receivedAt.trim() || null,
      raw_content: rawContent,
      base_url: normalizedBaseUrl,
      notes: notes.length ? notes : undefined,
      links: links.length ? links : undefined,
    })
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerHeader title="New Opportunity" />
      <DrawerContent>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-medium">
              Source
              <select
                aria-label="Source"
                value={source}
                onChange={(e) => setSource(e.target.value as OpportunitySource)}
                className="mt-1 h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
              >
                {SOURCE_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <DatePicker
              label="Received"
              value={receivedAt}
              onChange={setReceivedAt}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-medium">
              Sender
              <Input
                aria-label="Sender"
                placeholder="Recruiter name"
                value={sender}
                onChange={(e) => setSender(e.target.value)}
                className="mt-1"
              />
            </label>
            <label className="block text-xs font-medium">
              Sender email
              <Input
                aria-label="Sender email"
                placeholder="recruiter@company.com"
                value={senderEmail}
                onChange={(e) => setSenderEmail(e.target.value)}
                className="mt-1"
              />
            </label>
          </div>
          <label className="block text-xs font-medium">
            Subject
            <Input
              aria-label="Subject"
              placeholder="Message subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="mt-1"
            />
          </label>
          <label className="block text-xs font-medium">
            Base URL (optional)
            <Input
              type="url"
              aria-label="Base URL"
              placeholder="https://www.linkedin.com/posts/…"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="mt-1"
            />
            <span className="text-2xs text-muted-foreground font-normal">
              Canonical page the opportunity came from, e.g. the LinkedIn post
            </span>
          </label>
          <label className="block text-xs font-medium">
            Message
            <Textarea
              aria-label="Message"
              placeholder="Paste the inbound message or email here…"
              value={rawContent}
              onChange={(e) => setRawContent(e.target.value)}
              rows={10}
              className="mt-1"
            />
          </label>

          {/* Notes (optional) */}
          <div className="rounded-lg border p-2 space-y-2">
            <p className="text-2xs text-muted-foreground">Notes (optional)</p>
            {notes.length > 0 && (
              <ul className="space-y-1 max-h-24 overflow-y-auto">
                {notes.map((note, i) => (
                  <li
                    key={`${note.title ?? ''}-${i}`}
                    className="flex items-start gap-1 rounded border bg-muted/50 px-2 py-1 text-2xs"
                  >
                    <span className="flex-1 min-w-0">
                      {note.title && <span className="font-semibold">{note.title}: </span>}
                      {note.content}
                    </span>
                    <button
                      type="button"
                      aria-label={`Remove note ${i + 1}`}
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => setNotes((items) => items.filter((_, j) => j !== i))}
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="space-y-1">
              <Input
                aria-label="New note title"
                placeholder="Note title (e.g. Extra context)"
                value={noteTitle}
                onChange={(e) => setNoteTitle(e.target.value)}
              />
              <div className="flex gap-1">
                <Textarea
                  aria-label="New note content"
                  placeholder="Paste extra text (JD snippets, requirements)…"
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleAddNote()
                    }
                  }}
                  className="min-w-0 flex-1"
                  rows={2}
                />
                <Button
                  type="button"
                  onClick={handleAddNote}
                  disabled={!noteContent.trim()}
                  size="sm"
                  variant="outline"
                  aria-label="Add note"
                  className="shrink-0 self-end"
                >
                  <Plus className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>

          {/* Links (optional) */}
          <div className="rounded-lg border p-2 space-y-2">
            <p className="text-2xs text-muted-foreground">Links (optional)</p>
            {links.length > 0 && (
              <ul className="space-y-1 max-h-24 overflow-y-auto">
                {links.map((link, i) => (
                  <li
                    key={`${link.url}-${i}`}
                    className="flex items-start gap-1 rounded border bg-muted/50 px-2 py-1 text-2xs"
                  >
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex-1 min-w-0 text-primary hover:underline break-all"
                    >
                      {link.url}
                      {link.title ? ` — ${link.title}` : ''}
                    </a>
                    <button
                      type="button"
                      aria-label={`Remove link ${i + 1}`}
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => setLinks((items) => items.filter((_, j) => j !== i))}
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <Input
              type="url"
              aria-label="New link URL"
              placeholder="URL (https://…)"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddLink()}
            />
            <Input
              aria-label="New link title"
              placeholder={`Link title (${LINK_TITLE_PRESETS.join(', ')}, or custom)`}
              value={linkTitle}
              onChange={(e) => setLinkTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddLink()}
            />
            <Button
              type="button"
              onClick={handleAddLink}
              disabled={!linkUrl.trim()}
              size="sm"
              variant="outline"
              className="w-full"
            >
              <Plus className="w-3 h-3 mr-1" /> Add link
            </Button>
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>
      </DrawerContent>
      <DrawerFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={submitting || !rawContent.trim()}>
          {submitting ? 'Saving…' : 'Save opportunity'}
        </Button>
      </DrawerFooter>
    </Drawer>
  )
}

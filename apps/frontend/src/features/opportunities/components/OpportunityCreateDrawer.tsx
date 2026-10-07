'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader } from '@/shared/components/Drawer'
import type { CreateOpportunityRequest, OpportunitySource } from '@/entities/opportunity/types'

interface OpportunityCreateDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateOpportunityRequest) => void
  submitting?: boolean
  error?: string | null
}

const SOURCE_OPTIONS: OpportunitySource[] = ['manual', 'gmail', 'linkedin']

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

  useEffect(() => {
    if (!open) {
      setSource('manual')
      setSender('')
      setSenderEmail('')
      setSubject('')
      setReceivedAt('')
      setRawContent('')
    }
  }, [open ])

  const handleSubmit = () => {
    onSubmit({
      source,
      sender: sender.trim() || null,
      sender_email: senderEmail.trim() || null,
      subject: subject.trim() || null,
      received_at: receivedAt.trim() || null,
      raw_content: rawContent,
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
            <label className="block text-xs font-medium">
              Received
              <Input
                aria-label="Received"
                type="date"
                value={receivedAt}
                onChange={(e) => setReceivedAt(e.target.value)}
                className="mt-1"
              />
            </label>
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

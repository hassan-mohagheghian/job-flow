'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/shared/ui/button'
import { Textarea } from '@/shared/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { DEBOUNCE_DELAY } from '@/shared/config/constants'

interface DismissOpportunityDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  opportunityTitle?: string
  onDismiss: (note: string) => void
  isPending?: boolean
}

export function DismissOpportunityDialog({
  open,
  onOpenChange,
  opportunityTitle,
  onDismiss,
  isPending,
}: DismissOpportunityDialogProps) {
  const [note, setNote] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (open) {
      setNote('')
      setTimeout(() => textareaRef.current?.focus(), DEBOUNCE_DELAY)
    }
  }, [open])

  const handleDismiss = () => {
    onDismiss(note.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleDismiss()
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Dismiss opportunity</DialogTitle>
          <DialogDescription>
            {opportunityTitle ? `Dismiss "${opportunityTitle}"?` : 'Dismiss this opportunity?'} It
            will be hidden from the default list. The reason is saved to the follow-up trail.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Textarea
            ref={textareaRef}
            placeholder="Why are you dismissing this? (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            className="text-xs"
          />
          <p className="text-2xs text-muted-foreground">
            Press <kbd className="px-1 py-0.5 rounded bg-muted text-foreground text-2xs font-mono">Ctrl+Enter</kbd> to dismiss
          </p>
        </div>
        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDismiss} disabled={isPending}>
            {isPending ? 'Dismissing…' : 'Dismiss'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

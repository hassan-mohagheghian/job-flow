'use client'

import { useState } from 'react'
import { MapTrifold } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { useCreateRoadmapMutation } from '@/entities/roadmap/hooks'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Textarea } from '@/shared/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/ui/dialog'

export function RoadmapCreateDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const createRoadmap = useCreateRoadmapMutation()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [goalTitle, setGoalTitle] = useState('')

  const handleSubmit = () => {
    createRoadmap.mutate(
      {
        title,
        description,
        goal: { type: 'CUSTOM', title: goalTitle },
      },
      {
        onSuccess: () => {
          toast.success('Roadmap created')
          setTitle('')
          setDescription('')
          setGoalTitle('')
          onOpenChange(false)
        },
        onError: () => toast.error('Failed to create roadmap'),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapTrifold className="w-4 h-4 text-emerald-500" />
            New Roadmap
          </DialogTitle>
          <DialogDescription>Create a manual roadmap and set its goal.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="rc-title">Title</Label>
            <Input
              id="rc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Advance to senior manager"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="rc-description">Description</Label>
            <Textarea
              id="rc-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="rc-goal">Goal</Label>
            <Input
              id="rc-goal"
              value={goalTitle}
              onChange={(e) => setGoalTitle(e.target.value)}
              placeholder="e.g. Land a senior role in 12 months"
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} disabled={!title.trim() || createRoadmap.isPending}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
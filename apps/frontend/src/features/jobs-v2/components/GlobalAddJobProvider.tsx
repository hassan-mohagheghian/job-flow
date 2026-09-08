'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { usePathname } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus } from '@phosphor-icons/react'
import CreateEntityDrawer, {
  type CreateEntityFormData,
} from '@/shared/components/CreateEntityDrawer'
import { useCreateJob } from '@/features/jobs-v2/hooks/useCreateJob'
import { JobDetailDrawer } from '@/features/jobs-v2/components/JobDetailDrawer'
import { JobEditDrawer } from '@/features/jobs-v2/components/JobEditDrawer'
import { ProcessingDrawer } from '@/features/jobs-v2/components/ProcessingDrawer'
import { jobApi } from '@/entities/job/api'
import { readClipboardUrl } from '@/shared/lib/clipboard'
import {
  extractUrlFromDataTransfer,
  dataTransferHasUrl,
} from '@/shared/lib/url-drag'

interface GlobalAddJobContextValue {
  /** Open the Add Job drawer, prefilling the URL from the clipboard. */
  openAddJob: () => void
  /** Open the Add Job drawer pre-filled with the given URL. */
  openAddJobWithUrl: (url: string) => void
}

const GlobalAddJobContext = createContext<GlobalAddJobContextValue>({
  openAddJob: () => {},
  openAddJobWithUrl: () => {},
})

export function useGlobalAddJob() {
  return useContext(GlobalAddJobContext)
}

/**
 * Global drag-and-drop job import, active on every page EXCEPT the Jobs pages
 * (`/jobs*`), which keep their own drop overlay + Add Job drawer.
 *
 * Dragging a link from another browser tab anywhere into the app shows a
 * "Drop to add job" indicator; dropping opens the pre-filled Add Job drawer
 * (never auto-creates — the user then chooses Add or Add & Queue).
 */
export function GlobalAddJobProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const queryClient = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [clipboardUrl, setClipboardUrl] = useState<string | null>(null)
  const [detailJobId, setDetailJobId] = useState<string | null>(null)
  const [editJobId, setEditJobId] = useState<string | null>(null)
  const [queueOpen, setQueueOpen] = useState(false)
  const [queueReloadKey, setQueueReloadKey] = useState(0)
  const [dragging, setDragging] = useState(false)
  const depthRef = useRef(0)

  const isJobsRoute = pathname?.startsWith('/jobs') ?? false

  const { createJob, submitting, error, existingJobId, existingJob, clearError } =
    useCreateJob()

  const openAddJobWithUrl = useCallback((url: string) => {
    setClipboardUrl(url)
    setDrawerOpen(true)
  }, [])

  const openAddJob = useCallback(async () => {
    const url = await readClipboardUrl()
    setClipboardUrl(url)
    setDrawerOpen(true)
  }, [])

  const handleCreateJob = useCallback(
    async (data: CreateEntityFormData) => {
      const result = await createJob({
        job_post_url: data.job_post_url ?? '',
        job_title: data.job_title,
        links: data.links,
        notes: data.notes.map((n) => ({ title: n.title || '', content: n.content })),
        queue: data.queue,
      })
      if (result) {
        toast.success(data.queue ? 'Job created and queued' : 'Job created successfully')
        setDrawerOpen(false)
        queryClient.invalidateQueries({ queryKey: ['jobs'] })
        if (data.queue) {
          setQueueReloadKey((k) => k + 1)
          setQueueOpen(true)
        }
      }
    },
    [createJob, queryClient]
  )

  const handleReprocess = useCallback(
    (id: string) => {
      jobApi
        .processJob(id)
        .then(() => {
          setQueueReloadKey((k) => k + 1)
          setQueueOpen(true)
        })
        .catch(() => toast.error('Failed to queue processing'))
    },
    []
  )

  useEffect(() => {
    if (isJobsRoute) return
    const handleDragEnter = (e: DragEvent) => {
      if (e.defaultPrevented || !dataTransferHasUrl(e.dataTransfer)) return
      depthRef.current += 1
      setDragging(true)
    }
    const handleDragOver = (e: DragEvent) => {
      if (e.defaultPrevented || !dataTransferHasUrl(e.dataTransfer)) return
      e.preventDefault()
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
    }
    const handleDragLeave = (e: DragEvent) => {
      if (e.defaultPrevented || !dataTransferHasUrl(e.dataTransfer)) return
      depthRef.current = Math.max(0, depthRef.current - 1)
      if (depthRef.current === 0) setDragging(false)
    }
    const handleDrop = (e: DragEvent) => {
      if (e.defaultPrevented) return
      depthRef.current = 0
      setDragging(false)
      const url = extractUrlFromDataTransfer(e.dataTransfer)
      if (!url) return
      e.preventDefault()
      openAddJobWithUrl(url)
    }
    document.addEventListener('dragenter', handleDragEnter)
    document.addEventListener('dragover', handleDragOver)
    document.addEventListener('dragleave', handleDragLeave)
    document.addEventListener('drop', handleDrop)
    return () => {
      document.removeEventListener('dragenter', handleDragEnter)
      document.removeEventListener('dragover', handleDragOver)
      document.removeEventListener('dragleave', handleDragLeave)
      document.removeEventListener('drop', handleDrop)
    }
  }, [isJobsRoute, openAddJobWithUrl])

  return (
    <GlobalAddJobContext.Provider value={{ openAddJob, openAddJobWithUrl }}>
      {children}
      {!isJobsRoute && dragging && (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/60">
          <div className="rounded-lg border-2 border-dashed border-emerald-500/60 bg-card px-6 py-4 flex items-center gap-2 text-sm font-medium text-foreground shadow-lg">
            <Plus className="w-4 h-4 text-emerald-500" />
            Drop to add job
          </div>
        </div>
      )}
      {!isJobsRoute && (
        <>
          <ProcessingDrawer
            open={queueOpen}
            onOpenChange={setQueueOpen}
            reloadKey={queueReloadKey}
          />
          <JobDetailDrawer
            jobId={detailJobId}
            onOpenChange={setDetailJobId}
            onEdit={setEditJobId}
            onReprocess={handleReprocess}
          />
          <JobEditDrawer jobId={editJobId} onOpenChange={setEditJobId} />
          <CreateEntityDrawer
            mode="job"
            open={drawerOpen}
            onOpenChange={(open) => {
              setDrawerOpen(open)
              if (!open) clearError()
            }}
            onSubmit={handleCreateJob}
            submitting={submitting}
            error={error}
            clipboardUrl={clipboardUrl}
            existingJob={existingJob}
            onViewJobDetails={(id) => setDetailJobId(id)}
            errorLink={
              existingJobId
                ? {
                    label: 'Open application',
                    href: `/jobs/${encodeURIComponent(existingJobId)}/application`,
                  }
                : null
            }
          />
        </>
      )}
    </GlobalAddJobContext.Provider>
  )
}

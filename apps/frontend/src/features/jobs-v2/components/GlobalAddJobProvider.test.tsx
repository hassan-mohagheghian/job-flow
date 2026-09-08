import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GlobalAddJobProvider } from './GlobalAddJobProvider'

const pathnameState = vi.hoisted(() => ({ value: '/companies' }))

vi.mock('next/navigation', () => ({
  usePathname: () => pathnameState.value,
}))

vi.mock('@/shared/components/CreateEntityDrawer', () => ({
  default: ({ open, clipboardUrl }: { open: boolean; clipboardUrl?: string | null }) =>
    open ? <div data-testid="add-job-drawer">url:{clipboardUrl}</div> : null,
}))

vi.mock('@/features/jobs-v2/components/JobDetailDrawer', () => ({
  JobDetailDrawer: () => null,
}))
vi.mock('@/features/jobs-v2/components/JobEditDrawer', () => ({
  JobEditDrawer: () => null,
}))
vi.mock('@/features/jobs-v2/components/ProcessingDrawer', () => ({
  ProcessingDrawer: () => null,
}))

function urlDataTransfer(url: string): DataTransfer {
  const values: Record<string, string> = {
    'text/uri-list': url,
    'text/plain': url,
  }
  return {
    types: Object.keys(values),
    getData: (type: string) => values[type] ?? '',
    dropEffect: '',
  } as unknown as DataTransfer
}

function renderProvider() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <GlobalAddJobProvider>
        <div>page content</div>
      </GlobalAddJobProvider>
    </QueryClientProvider>
  )
}

describe('GlobalAddJobProvider', () => {
  beforeEach(() => {
    pathnameState.value = '/companies'
  })

  it('opens the pre-filled Add Job drawer on document drop outside /jobs', () => {
    renderProvider()
    fireEvent.drop(document.body, { dataTransfer: urlDataTransfer('https://example.com/job') })
    expect(screen.getByTestId('add-job-drawer')).toHaveTextContent('url:https://example.com/job')
  })

  it('shows the drop hint while a url is dragged over the page', () => {
    renderProvider()
    fireEvent.dragEnter(document.body, { dataTransfer: urlDataTransfer('https://example.com/job') })
    expect(screen.getByText('Drop to add job')).toBeInTheDocument()
  })

  it('ignores drops without a url', () => {
    renderProvider()
    const dt = { types: ['Files'], getData: () => '' } as unknown as DataTransfer
    fireEvent.drop(document.body, { dataTransfer: dt })
    expect(screen.queryByTestId('add-job-drawer')).not.toBeInTheDocument()
  })

  it('stays inactive on /jobs routes (page owns its own overlay)', () => {
    pathnameState.value = '/jobs'
    renderProvider()
    fireEvent.dragEnter(document.body, { dataTransfer: urlDataTransfer('https://example.com/job') })
    expect(screen.queryByText('Drop to add job')).not.toBeInTheDocument()
    fireEvent.drop(document.body, { dataTransfer: urlDataTransfer('https://example.com/job') })
    expect(screen.queryByTestId('add-job-drawer')).not.toBeInTheDocument()
  })
})

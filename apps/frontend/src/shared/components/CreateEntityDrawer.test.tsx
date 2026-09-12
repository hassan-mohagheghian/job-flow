import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CreateEntityDrawer, { type CreateEntityFormData } from './CreateEntityDrawer'
import { applicationApi } from '@/entities/application/api'

vi.mock('@/shared/components/Drawer', () => ({
  Drawer: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DrawerHeader: ({ title, actions, children }: any) => <div>{title}{actions}{children}</div>,
  DrawerContent: ({ children }: any) => <div>{children}</div>,
  DrawerFooter: ({ children }: any) => <div>{children}</div>,
}))

const readClipboardUrlMock = vi.fn()
vi.mock('@/shared/lib/clipboard', () => ({
  readClipboardUrl: (...args: any[]) => readClipboardUrlMock(...args),
}))

vi.mock('@/entities/application/api', () => ({
  applicationApi: {
    getByJob: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  readClipboardUrlMock.mockReset()
  readClipboardUrlMock.mockResolvedValue(null)
})

function renderDrawer(mode: 'job' | 'company', onSubmit: (data: CreateEntityFormData) => void = vi.fn()) {
  return render(
    <CreateEntityDrawer open onOpenChange={vi.fn()} mode={mode} onSubmit={onSubmit} />
  )
}

describe('CreateEntityDrawer — job mode', () => {
  it('renders the job fields and title', () => {
    renderDrawer('job')
    expect(screen.getByText('Import Job')).toBeInTheDocument()
    expect(screen.getByText('Job Post URL')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Senior Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Additional Links')).toBeInTheDocument()
    expect(screen.getByText('Notes')).toBeInTheDocument()
  })

  it('focuses the Job Post URL input on open', () => {
    renderDrawer('job')
    expect(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...')).toHaveFocus()
  })

  it('disables submit until a valid URL is entered', () => {
    renderDrawer('job')
    const addButton = screen.getByText('Add') as HTMLButtonElement
    const queueButton = screen.getByText('Add & Queue') as HTMLButtonElement
    expect(addButton.disabled).toBe(true)
    expect(queueButton.disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      target: { value: 'https://example.com/job' },
    })
    expect(addButton.disabled).toBe(false)
    expect(queueButton.disabled).toBe(false)
  })

  it('Add submits without queue', () => {
    const onSubmit = vi.fn()
    renderDrawer('job', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      target: { value: 'https://example.com/job' },
    })
    fireEvent.click(screen.getByText('Add'))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ queue: false, job_post_url: 'https://example.com/job' }))
  })

  it('Add & Queue submits with queue true', () => {
    const onSubmit = vi.fn()
    renderDrawer('job', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      target: { value: 'https://example.com/job' },
    })
    fireEvent.click(screen.getByText('Add & Queue'))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ queue: true, job_post_url: 'https://example.com/job' }))
  })

  it('Enter in the URL input adds and queues the job', () => {
    const onSubmit = vi.fn()
    renderDrawer('job', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      target: { value: 'https://example.com/job' },
    })
    fireEvent.keyDown(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      key: 'Enter',
    })
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ queue: true, job_post_url: 'https://example.com/job' }))
  })

  it('Enter in the job title input adds and queues the job', () => {
    const onSubmit = vi.fn()
    renderDrawer('job', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      target: { value: 'https://example.com/job' },
    })
    fireEvent.keyDown(screen.getByPlaceholderText('Senior Backend Engineer'), {
      key: 'Enter',
    })
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ queue: true, job_post_url: 'https://example.com/job' }))
  })

  it('Enter with an invalid URL does not submit', () => {
    const onSubmit = vi.fn()
    renderDrawer('job', onSubmit)
    fireEvent.keyDown(screen.getByPlaceholderText('https://linkedin.com/jobs/view/...'), {
      key: 'Enter',
    })
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('CreateEntityDrawer — company mode', () => {
  it('renders the company fields in primary link → name → links → notes order', () => {
    renderDrawer('company')
    expect(screen.getByText('Add Company')).toBeInTheDocument()
    const primary = screen.getByText('Primary Link')
    const name = screen.getByText('Company Name')
    const links = screen.getByText('Additional Links')
    const notes = screen.getByText('Notes')
    const before = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
    expect(before(primary, name)).toBe(true)
    expect(before(name, links)).toBe(true)
    expect(before(links, notes)).toBe(true)
  })

  it('disables submit until a primary link URL is entered', () => {
    renderDrawer('company')
    const addButton = screen.getByText('Add') as HTMLButtonElement
    expect(addButton.disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText('Acme GmbH'), {
      target: { value: 'Acme GmbH' },
    })
    expect(addButton.disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText('https://acme.example'), {
      target: { value: 'https://acme.example' },
    })
    expect(addButton.disabled).toBe(false)
  })

  it('keeps Add & Process disabled', () => {
    renderDrawer('company')
    const processButton = screen.getByText('Add & Process') as HTMLButtonElement
    expect(processButton.disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText('https://acme.example'), {
      target: { value: 'https://acme.example' },
    })
    expect(processButton.disabled).toBe(true)
  })

  it('Add submits name, primary link and queue false', () => {
    const onSubmit = vi.fn()
    renderDrawer('company', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://acme.example'), {
      target: { value: 'https://acme.example' },
    })
    fireEvent.change(screen.getByPlaceholderText('Acme GmbH'), {
      target: { value: 'Acme GmbH' },
    })
    fireEvent.click(screen.getByText('Website'))
    fireEvent.click(screen.getByText('Add'))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'company',
      name: 'Acme GmbH',
      queue: false,
      primaryLink: { url: 'https://acme.example', title: 'Website' },
    }))
  })

  it('disables the primary title preset in the additional link selector', () => {
    renderDrawer('company')
    fireEvent.click(screen.getByText('LinkedIn'))
    fireEvent.click(screen.getByText('Add Link'))
    const linkedInButtons = screen.getAllByText('LinkedIn')
    const disabledLinkedIn = linkedInButtons.find((b) => (b as HTMLButtonElement).disabled)
    expect(disabledLinkedIn).toBeTruthy()
    const websiteButtons = screen.getAllByText('Website')
    expect(websiteButtons.every((b) => !(b as HTMLButtonElement).disabled)).toBe(true)
  })

  it('sends the primary link first in the links array', () => {
    const onSubmit = vi.fn()
    renderDrawer('company', onSubmit)
    fireEvent.change(screen.getByPlaceholderText('https://acme.example'), {
      target: { value: 'https://acme.example' },
    })
    fireEvent.click(screen.getByText('Add Link'))
    fireEvent.change(screen.getAllByPlaceholderText('https://...')[0], {
      target: { value: 'https://careers.acme.example' },
    })
    fireEvent.click(screen.getByText('Careers'))
    fireEvent.click(screen.getAllByText('Add')[0])
    fireEvent.click(screen.getByText('Add'))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      links: [{ url: 'https://careers.acme.example', title: 'Careers' }],
    }))
    const data = (onSubmit.mock.calls[0][0] as CreateEntityFormData)
    expect(data.primaryLink?.url).toBe('https://acme.example')
  })
})

describe('CreateEntityDrawer — error state', () => {
  it('renders the error message', () => {
    render(
      <CreateEntityDrawer open onOpenChange={vi.fn()} mode="job" onSubmit={vi.fn()} error="Something failed" />
    )
    expect(screen.getByText('Something failed')).toBeInTheDocument()
  })

  it('renders an error link when errorLink is provided', () => {
    render(
      <CreateEntityDrawer
        open
        onOpenChange={vi.fn()}
        mode="job"
        onSubmit={vi.fn()}
        error="A Job with the same primary URL already exists."
        errorLink={{ label: 'Open existing job', href: '/jobs?job=job-dup' }}
      />
    )
    const link = screen.getByRole('link', { name: 'Open existing job' })
    expect(link).toHaveAttribute('href', '/jobs?job=job-dup')
  })

  it('does not render an error link when errorLink is null', () => {
    render(
      <CreateEntityDrawer open onOpenChange={vi.fn()} mode="job" onSubmit={vi.fn()} error="Something failed" />
    )
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('renders a summary of the existing job below the error', async () => {
    const existingJob = {
      id: 'job-dup',
      title: 'Senior Backend Engineer',
      company: 'Acme GmbH',
      location: 'Berlin',
      visa: 'Yes',
      salary: '€90k',
      employment_types: ['Full-time'],
      work_types: ['Remote'],
      overall_score: 85,
      fit_score: 80,
      success_score: 90,
      rank: 3,
      url: 'https://acme.example/careers/senior',
      company_id: null,
      company_type: 'Product',
      tracking_status: null,
      updated_at: null,
    }
    renderWithProviders(
      <CreateEntityDrawer
        open
        onOpenChange={vi.fn()}
        mode="job"
        onSubmit={vi.fn()}
        error="A Job with the same primary URL already exists."
        existingJob={existingJob}
      />
    )
    expect(screen.getByText('Senior Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Acme GmbH')).toBeInTheDocument()
    expect(screen.getByText('Berlin')).toBeInTheDocument()
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('#3')).toBeInTheDocument()
    const posting = screen.getByRole('link', { name: 'Open job posting' })
    expect(posting).toHaveAttribute('href', 'https://acme.example/careers/senior')
    expect(await screen.findByRole('button', { name: /mark expired/i })).toBeInTheDocument()
  })

  it('invokes onViewJobDetails when View full job details is clicked', () => {
    const onViewJobDetails = vi.fn()
    const existingJob = {
      id: 'job-dup',
      title: 'Senior Backend Engineer',
      company: null,
      company_id: null,
      company_type: null,
      location: null,
      visa: null,
      salary: null,
      employment_types: null,
      work_types: null,
      overall_score: null,
      fit_score: null,
      success_score: null,
      rank: null,
      tracking_status: null,
      url: null,
      updated_at: null,
    }
    renderWithProviders(
      <CreateEntityDrawer
        open
        onOpenChange={vi.fn()}
        mode="job"
        onSubmit={vi.fn()}
        error="A Job with the same primary URL already exists."
        existingJob={existingJob}
        onViewJobDetails={onViewJobDetails}
      />
    )
    fireEvent.click(screen.getByText('View full job details'))
    expect(onViewJobDetails).toHaveBeenCalledWith('job-dup')
  })
})

describe('CreateEntityDrawer — clipboard prefill', () => {
  it('prefills the job URL from the clipboard when the drawer opens', async () => {
    readClipboardUrlMock.mockResolvedValue('https://linkedin.com/jobs/view/123')
    renderDrawer('job')
    const urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/123'))
  })

  it('prefills the company primary link from the clipboard when the drawer opens', async () => {
    readClipboardUrlMock.mockResolvedValue('https://acme.example')
    renderDrawer('company')
    const urlInput = screen.getByPlaceholderText('https://acme.example') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://acme.example'))
  })

  it('leaves the URL empty when the clipboard has no link', async () => {
    renderDrawer('job')
    const urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(readClipboardUrlMock).toHaveBeenCalled())
    expect(urlInput.value).toBe('')
  })

  it('clears a stale URL and re-reads the clipboard on every open', async () => {
    readClipboardUrlMock.mockResolvedValue('https://linkedin.com/jobs/view/123')
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={vi.fn()} />
    )
    let urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/123'))

    // Simulate a programmatic close that bypasses the on-close reset: the stale
    // value survives in state.
    fireEvent.change(urlInput, { target: { value: 'https://stale.example' } })
    rerender(<CreateEntityDrawer open={false} onOpenChange={onOpenChange} mode="job" onSubmit={vi.fn()} />)

    readClipboardUrlMock.mockResolvedValue('https://linkedin.com/jobs/view/456')
    rerender(<CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={vi.fn()} />)
    urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/456'))
    expect(readClipboardUrlMock).toHaveBeenCalledTimes(2)
  })

  it('prefills the job URL from a gesture-captured clipboardUrl prop', async () => {
    render(
      <CreateEntityDrawer open onOpenChange={vi.fn()} mode="job" onSubmit={vi.fn()} clipboardUrl="https://linkedin.com/jobs/view/999" />
    )
    const urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/999'))
    expect(readClipboardUrlMock).not.toHaveBeenCalled()
  })

  it('prefills the company primary link from a gesture-captured clipboardUrl prop', async () => {
    render(
      <CreateEntityDrawer open onOpenChange={vi.fn()} mode="company" onSubmit={vi.fn()} clipboardUrl="https://acme.example" />
    )
    const urlInput = screen.getByPlaceholderText('https://acme.example') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://acme.example'))
    expect(readClipboardUrlMock).not.toHaveBeenCalled()
  })

  it('falls back to reading the clipboard when clipboardUrl is not provided', async () => {
    readClipboardUrlMock.mockResolvedValue('https://linkedin.com/jobs/view/123')
    renderDrawer('job')
    const urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/123'))
    expect(readClipboardUrlMock).toHaveBeenCalledTimes(1)
  })

  it('prefills a gesture-captured clipboardUrl again on the reopen after a successful Add', async () => {
    const onSubmit = vi.fn()
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <CreateEntityDrawer open={false} onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} clipboardUrl="https://linkedin.com/jobs/view/999" />
    )
    rerender(<CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} clipboardUrl="https://linkedin.com/jobs/view/999" />)
    let urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/999'))

    fireEvent.click(screen.getByText('Add'))
    expect(onSubmit).toHaveBeenCalled()
    fireEvent.click(screen.getByText('Cancel'))
    expect(onOpenChange).toHaveBeenCalledWith(false)

    rerender(<CreateEntityDrawer open={false} onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} clipboardUrl="https://linkedin.com/jobs/view/999" />)
    rerender(<CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} clipboardUrl="https://linkedin.com/jobs/view/999" />)
    urlInput = screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement
    await waitFor(() => expect(urlInput.value).toBe('https://linkedin.com/jobs/view/999'))
  })

  it('re-reads and prefills the clipboard again on the reopen after a successful Add', async () => {
    readClipboardUrlMock.mockResolvedValue('https://linkedin.com/jobs/view/123')
    const onSubmit = vi.fn()
    const onOpenChange = vi.fn()
    const { rerender } = render(
      <CreateEntityDrawer open={false} onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} />
    )

    rerender(<CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} />)
    await waitFor(() => expect((screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement).value).toBe('https://linkedin.com/jobs/view/123'))
    expect(readClipboardUrlMock).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByText('Add'))
    fireEvent.click(screen.getByText('Cancel'))
    rerender(<CreateEntityDrawer open={false} onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} />)
    rerender(<CreateEntityDrawer open onOpenChange={onOpenChange} mode="job" onSubmit={onSubmit} />)
    await waitFor(() => expect((screen.getByPlaceholderText('https://linkedin.com/jobs/view/...') as HTMLInputElement).value).toBe('https://linkedin.com/jobs/view/123'))
    expect(readClipboardUrlMock).toHaveBeenCalledTimes(2)
  })
})

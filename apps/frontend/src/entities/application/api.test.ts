import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { applicationApi } from './api'

const fetchMock = vi.fn()

beforeAll(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.resetAllMocks()
})

function ok(body: unknown) {
  return { ok: true, json: () => Promise.resolve(body) }
}

describe('applicationApi', () => {
  it('creates an application with a job_id', async () => {
    const detail = { id: 'app-1', job_id: 'job-1', status: 'seen', follow_ups: [], documents: [] }
    fetchMock.mockResolvedValue(ok(detail))

    const result = await applicationApi.create('job-1')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ job_id: 'job-1', seen_at: null })
    expect(result.id).toBe('app-1')
  })

  it('creates an application with a seen_at timestamp', async () => {
    const detail = { id: 'app-1', job_id: 'job-1', status: 'seen', follow_ups: [], documents: [] }
    fetchMock.mockResolvedValue(ok(detail))

    await applicationApi.create('job-1', '2026-07-01T08:00:00Z')

    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body)).toEqual({ job_id: 'job-1', seen_at: '2026-07-01T08:00:00Z' })
  })

  it('updates an application status', async () => {
    const detail = { id: 'app-1', job_id: 'job-1', status: 'applied', applied_at: '2026-08-11T10:00:00Z', follow_ups: [], documents: [] }
    fetchMock.mockResolvedValue(ok(detail))

    await applicationApi.update('app-1', { status: 'applied', applied_at: '2026-08-11T10:00:00Z' })

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/app-1')
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ status: 'applied', applied_at: '2026-08-11T10:00:00Z' })
  })

  it('updates a timeline event changed_at', async () => {
    const event = { id: 'ev-1', application_id: 'app-1', status: 'applied', changed_at: '2026-08-02T10:30:00+02:00' }
    fetchMock.mockResolvedValue(ok(event))

    await applicationApi.updateTimeline('ev-1', '2026-08-02T10:30:00+02:00')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/timeline/ev-1')
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ changed_at: '2026-08-02T10:30:00+02:00' })
  })

  it('deletes a timeline event', async () => {
    fetchMock.mockResolvedValue(ok({}))

    await applicationApi.deleteTimeline('ev-1')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/timeline/ev-1')
    expect(options.method).toBe('DELETE')
  })

  it('gets the application for a job', async () => {
    fetchMock.mockResolvedValue(ok({ id: 'app-1', job_id: 'job-1', status: 'preparing', follow_ups: [], documents: [] }))

    await applicationApi.getByJob('job-1')

    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/by-job/job-1')
  })

  it('gets the application status distribution', async () => {
    const distribution = {
      items: [
        { status: 'applied', count: 12 },
        { status: 'interview', count: 4 },
      ],
      total: 16,
    }
    fetchMock.mockResolvedValue(ok(distribution))

    const result = await applicationApi.statusDistribution()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/applications/status-distribution')
    expect(result.total).toBe(16)
  })

  it('adds a follow-up', async () => {
    fetchMock.mockResolvedValue(ok({ id: 'fu-1', application_id: 'app-1', scheduled_at: null, note: 'ping', completed_at: null }))

    await applicationApi.addFollowUp('app-1', { note: 'ping' })

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/app-1/follow-ups')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ note: 'ping' })
  })

  it('generates a roadmap', async () => {
    fetchMock.mockResolvedValue(ok({ execution_id: 'exec-1', status: 'queued', artifact: 'roadmap' }))

    const result = await applicationApi.generateRoadmap('app-1')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/app-1/roadmap/generate')
    expect(options.method).toBe('POST')
    expect(result.artifact).toBe('roadmap')
  })

  it('generates a cover letter document', async () => {
    fetchMock.mockResolvedValue(ok({ execution_id: 'exec-2', status: 'queued', artifact: 'cover_letter' }))

    await applicationApi.generateDocument('app-1', 'cover_letter')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/app-1/documents/cover_letter/generate')
    expect(options.method).toBe('POST')
  })

  it('updates a document content', async () => {
    fetchMock.mockResolvedValue(ok({ id: 'doc-1', application_id: 'app-1', document_type: 'tailored_resume', version: 2, content: '# Updated' }))

    await applicationApi.updateDocument('doc-1', '# Updated')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/documents/doc-1')
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ content: '# Updated' })
  })

  it('deletes a document', async () => {
    fetchMock.mockResolvedValue(ok({ status: 'deleted' }))

    await applicationApi.deleteDocument('doc-1')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/applications/documents/doc-1')
    expect(options.method).toBe('DELETE')
  })

  it('rejects when generation fails', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 409, json: () => Promise.resolve({ error: 'an execution is already running' }) })

    await expect(applicationApi.generateRoadmap('app-1')).rejects.toThrow(/already running/)
  })

  it('downloads a document as PDF', async () => {
    const blob = new Blob(['%PDF-fake'], { type: 'application/pdf' })
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    })
    const createSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake')
    const clickSpy = vi.fn()
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(document, 'createElement').mockReturnValue({ click: clickSpy, href: '', download: '' } as unknown as HTMLAnchorElement)

    await applicationApi.downloadPdf('doc-1', 'resume.pdf')

    expect(fetchMock.mock.calls[0][0]).toBe('/api/applications/documents/doc-1/pdf')
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeSpy).toHaveBeenCalled()

    createSpy.mockRestore()
    revokeSpy.mockRestore()
  })
})

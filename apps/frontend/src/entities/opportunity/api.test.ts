import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { opportunityApi } from './api'

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

describe('opportunityApi', () => {
  it('creates a manual opportunity via POST /opportunities', async () => {
    const body = { id: 'opp-1', status: 'new', duplicate: false }
    fetchMock.mockResolvedValue(ok(body))

    const result = await opportunityApi.create({ source: 'manual', raw_content: 'Hi!' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/opportunities')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(result.id).toBe('opp-1')
  })

  it('lists opportunities newest-first via GET /opportunities', async () => {
    const body = { items: [{ id: 'opp-2' }, { id: 'opp-1' }], total: 2 }
    fetchMock.mockResolvedValue(ok(body))

    const result = await opportunityApi.list({ status: 'new' })

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/opportunities')
    expect(String(fetchMock.mock.calls[0][0])).toContain('status=new')
    expect(result.total).toBe(2)
  })

  it('fetches detail, processes, links, updates status and deletes', async () => {
    fetchMock.mockResolvedValue(ok({ id: 'opp-1' }))
    await opportunityApi.getDetail('opp-1')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/opportunities/opp-1')

    fetchMock.mockResolvedValue(ok({ id: 'opp-1', status: 'evaluated' }))
    await opportunityApi.process('opp-1')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/opportunities/opp-1/process')

    fetchMock.mockResolvedValue(ok({ id: 'opp-1' }))
    await opportunityApi.setLinks('opp-1', { job_id: 'job-1' })
    expect(fetchMock.mock.calls[2][0]).toBe('/api/opportunities/opp-1/links')

    fetchMock.mockResolvedValue(ok({ id: 'opp-1' }))
    await opportunityApi.setStatus('opp-1', 'applied')
    expect(fetchMock.mock.calls[3][0]).toBe('/api/opportunities/opp-1/status')

    fetchMock.mockResolvedValue({ ok: true, status: 204, json: () => Promise.resolve(undefined) })
    await opportunityApi.remove('opp-1')
    expect(fetchMock.mock.calls[4][0]).toBe('/api/opportunities/opp-1')
  })
})

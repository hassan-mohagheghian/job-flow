import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { jobApi } from './api'
import { sourceApi } from './sources'

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

describe('jobApi.timeline', () => {
  it('fetches per-day created-job counts from /jobs/timeline', async () => {
    const body = { days: [{ date: '2026-08-19', count: 3 }], total: 3 }
    fetchMock.mockResolvedValue(ok(body))

    const result = await jobApi.timeline()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/jobs/timeline')
    expect(result.total).toBe(3)
    expect(result.days[0]).toEqual({ date: '2026-08-19', count: 3 })
  })
})

describe('sourceApi.applicationStatusDistribution', () => {
  it('fetches job tracking-status counts from /jobs/tracking-status/distribution', async () => {
    const body = {
      items: [
        { status: 'not_applied', count: 9 },
        { status: 'applied', count: 2 },
      ],
      total: 11,
    }
    fetchMock.mockResolvedValue(ok(body))

    const result = await sourceApi.applicationStatusDistribution()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/jobs/tracking-status/distribution')
    expect(result.total).toBe(11)
    expect(result.items[0]).toEqual({ status: 'not_applied', count: 9 })
  })
})

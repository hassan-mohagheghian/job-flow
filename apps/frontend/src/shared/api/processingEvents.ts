import type { SSEEventEnvelope, SSEEventType } from '@/entities/processing/types'
import { AUTH_TOKEN_KEY, SSE_RECONNECT_BASE_DELAY, SSE_RECONNECT_MAX_DELAY } from '@/shared/config/constants'

let enableLogging = false
export function setSSELogging(enabled: boolean) { enableLogging = enabled }

// Prefer a direct backend connection when NEXT_PUBLIC_API_URL is baked in
// (local dev: avoids the Next dev-proxy gzip buffering documented in
// docs/api/sse/processing-events.md). Fall back to the same-origin relative
// URL — served via the /events/* rewrite in next.config.ts — because
// NEXT_PUBLIC_* is frozen at frontend build time and is empty/stale in the
// prebuilt terraform-docker image.
const SSE_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/events/processing`
  : '/events/processing'

const EVENT_TYPES: SSEEventType[] = [
  'execution.created',
  'execution.started',
  'execution.completed',
  'execution.failed',
  'execution.cancelled',
  'queue.entry.removed',
  'workflow.step.started',
  'workflow.step.progress',
  'workflow.step.completed',
  'workflow.step.failed',
]

type Listener = (type: SSEEventType, data: SSEEventEnvelope) => void

let es: EventSource | null = null
let listeners = new Set<Listener>()
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

function buildSSEUrl(): string | null {
  const token = getToken()
  if (!token) return null
  return `${SSE_BASE}?token=${encodeURIComponent(token)}`
}

function connect() {
  if (es || reconnectTimeout) return

  const url = buildSSEUrl()
  if (!url) return

  const socket = new EventSource(url)
  es = socket

  for (const type of EVENT_TYPES) {
    socket.addEventListener(type, (e) => {
      let data: SSEEventEnvelope
      try {
        data = JSON.parse((e as MessageEvent).data)
      } catch {
        return
      }
      for (const listener of listeners) {
        try {
          listener(type, data)
        } catch (err) {
          if (enableLogging) {
            console.error('[SSE] listener error', type, err)
          }
        }
      }
    })
  }

  socket.onopen = () => {
    reconnectAttempts = 0
  }

  socket.onerror = () => {
    socket.close()
    if (es === socket) es = null
    if (listeners.size === 0) return
    reconnectAttempts += 1
    const delay = Math.min(SSE_RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts - 1), SSE_RECONNECT_MAX_DELAY)
    reconnectTimeout = setTimeout(() => {
      reconnectTimeout = null
      connect()
    }, delay)
  }
}

function disconnect() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
  if (es) {
    es.close()
    es = null
  }
  reconnectAttempts = 0
}

export function subscribeProcessingEvents(listener: Listener): () => void {
  listeners.add(listener)
  connect()
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      disconnect()
    }
  }
}

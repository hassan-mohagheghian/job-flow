import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ApplicationStatusBadge } from './ApplicationStatusBadge'

describe('ApplicationStatusBadge', () => {
  it('renders the label for each status', () => {
    const cases = [
      { status: 'seen', label: 'Seen' },
      { status: 'preparing', label: 'Preparing' },
      { status: 'ready_to_apply', label: 'Ready to Apply' },
      { status: 'applied', label: 'Applied' },
      { status: 'rejected', label: 'Rejected' },
      { status: 'withdrawn', label: 'Withdrawn' },
      { status: 'expired', label: 'Expired' },
    ] as const

    for (const { status, label } of cases) {
      const { unmount } = render(<ApplicationStatusBadge status={status} />)
      expect(screen.getByText(label)).toBeInTheDocument()
      unmount()
    }
  })

  it('renders the raw value for an unknown status', () => {
    render(<ApplicationStatusBadge status={'custom' as never} />)
    expect(screen.getByText('custom')).toBeInTheDocument()
  })
})

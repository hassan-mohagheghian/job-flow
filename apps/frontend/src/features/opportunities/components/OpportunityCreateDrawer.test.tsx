import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { OpportunityCreateDrawer } from './OpportunityCreateDrawer'

describe('OpportunityCreateDrawer', () => {
  it('submits the pasted message with metadata', () => {
    const onSubmit = vi.fn()
    render(
      <OpportunityCreateDrawer
        open
        onOpenChange={vi.fn()}
        onSubmit={onSubmit}
        submitting={false}
        error={null}
      />,
    )

    fireEvent.change(screen.getByLabelText(/message/i), { target: { value: 'Hi Hassan, hiring?' } })
    fireEvent.change(screen.getByLabelText(/sender$/i), { target: { value: 'Jane' } })
    fireEvent.change(screen.getByLabelText(/subject/i), { target: { value: 'Backend role' } })
    fireEvent.click(screen.getByRole('button', { name: /received picker/i }))
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const expected = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-15`
    fireEvent.click(screen.getByRole('button', { name: expected }))
    fireEvent.click(screen.getByRole('button', { name: /save opportunity/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        source: 'manual',
        sender: 'Jane',
        subject: 'Backend role',
        received_at: expected,
        raw_content: 'Hi Hassan, hiring?',
      }),
    )
  })

  it('shows the backend error', () => {
    render(
      <OpportunityCreateDrawer
        open
        onOpenChange={vi.fn()}
        onSubmit={vi.fn()}
        submitting={false}
        error="Message is required"
      />,
    )
    expect(screen.getByText('Message is required')).toBeInTheDocument()
  })
})

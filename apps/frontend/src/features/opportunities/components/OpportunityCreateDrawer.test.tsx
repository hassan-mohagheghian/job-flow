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
        base_url: null,
        notes: undefined,
        links: undefined,
      }),
    )
  })

  it('normalizes the base URL scheme and passes notes and links', () => {
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
    fireEvent.change(screen.getByLabelText(/base url/i), {
      target: { value: 'www.linkedin.com/posts/jane-hiring' },
    })

    fireEvent.change(screen.getByLabelText(/new note content/i), {
      target: { value: 'Extra JD snippet.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add note/i }))

    fireEvent.change(screen.getByLabelText(/new link url/i), {
      target: { value: 'acme.example/careers' },
    })
    fireEvent.change(screen.getByLabelText(/new link title/i), { target: { value: 'Careers' } })
    fireEvent.click(screen.getByRole('button', { name: /add link/i }))

    fireEvent.click(screen.getByRole('button', { name: /save opportunity/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        raw_content: 'Hi Hassan, hiring?',
        base_url: 'https://www.linkedin.com/posts/jane-hiring',
        notes: [{ title: null, content: 'Extra JD snippet.' }],
        links: [{ title: 'Careers', url: 'https://acme.example/careers' }],
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

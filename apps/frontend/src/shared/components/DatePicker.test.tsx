import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { DatePicker, parseISODate, toISODate } from './DatePicker'

describe('date helpers', () => {
  it('formats and parses ISO dates', () => {
    expect(toISODate(2026, 8, 1)).toBe('2026-09-01')
    expect(parseISODate('2026-09-01')).toEqual({ year: 2026, month: 8, day: 1 })
    expect(parseISODate('')).toBeNull()
    expect(parseISODate('not-a-date')).toBeNull()
    expect(parseISODate('2026-02-30')).toBeNull()
  })
})

describe('DatePicker', () => {
  it('opens the calendar popup on icon click and picks a day', () => {
    const onChange = vi.fn()
    render(<DatePicker label="Received" value="" onChange={onChange} />)

    expect(screen.queryByLabelText(/received calendar/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /received picker/i }))
    expect(screen.getByLabelText(/received calendar/i)).toBeInTheDocument()

    const now = new Date()
    const expected = toISODate(now.getFullYear(), now.getMonth(), 15)
    fireEvent.click(screen.getByRole('button', { name: expected }))
    expect(onChange).toHaveBeenCalledWith(expected)
  })

  it('shows the current value and clears it', () => {
    const onChange = vi.fn()
    render(<DatePicker label="Received" value="2026-09-01" onChange={onChange} />)

    expect(screen.getByRole('button', { name: /received picker/i })).toHaveTextContent('2026-09-01')

    fireEvent.click(screen.getByRole('button', { name: /received picker/i }))
    const selected = screen.getByRole('button', { name: '2026-09-01' })
    expect(selected).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: /^clear$/i }))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('navigates months', () => {
    const onChange = vi.fn()
    render(<DatePicker label="Received" value="2026-09-15" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /received picker/i }))
    expect(screen.getByText('September 2026')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /next month/i }))
    expect(screen.getByText('October 2026')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /previous month/i }))
    fireEvent.click(screen.getByRole('button', { name: /previous month/i }))
    expect(screen.getByText('August 2026')).toBeInTheDocument()
    expect(onChange).not.toHaveBeenCalled()
  })
})

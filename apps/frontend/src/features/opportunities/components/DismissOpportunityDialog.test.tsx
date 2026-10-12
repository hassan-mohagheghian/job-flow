import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { DismissOpportunityDialog } from './DismissOpportunityDialog'

describe('DismissOpportunityDialog', () => {
  it('submits the dismiss reason', () => {
    const onDismiss = vi.fn()
    render(
      <DismissOpportunityDialog
        open
        onOpenChange={vi.fn()}
        opportunityTitle="Senior Backend Engineer"
        onDismiss={onDismiss}
        isPending={false}
      />,
    )

    expect(screen.getByText('Dismiss opportunity')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText(/why are you dismissing/i), {
      target: { value: 'Wrong seniority' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^dismiss$/i }))
    expect(onDismiss).toHaveBeenCalledWith('Wrong seniority')
  })

  it('dismisses without a reason', () => {
    const onDismiss = vi.fn()
    render(<DismissOpportunityDialog open onOpenChange={vi.fn()} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button', { name: /^dismiss$/i }))
    expect(onDismiss).toHaveBeenCalledWith('')
  })
})

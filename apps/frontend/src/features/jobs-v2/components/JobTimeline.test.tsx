import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { TooltipProvider } from '@/shared/ui/tooltip'
import { JobTimeline } from './JobTimeline'
import type { JobTimelineDay } from '@/entities/job/types'

const days: JobTimelineDay[] = [
  { date: '2026-08-19', count: 3, apply_count: 2 },
  { date: '2026-08-18', count: 5, apply_count: 0 },
  { date: '2026-07-30', count: 4 },
]

function renderTimeline(days: JobTimelineDay[]) {
  return render(
    <TooltipProvider>
      <JobTimeline days={days} />
    </TooltipProvider>,
  )
}

describe('JobTimeline', () => {
  it('renders the header', () => {
    renderTimeline(days)
    expect(screen.getByText('Jobs added')).toBeInTheDocument()
  })

  it('uses a wide, responsive timeline column', () => {
    renderTimeline(days)
    const panel = screen.getByRole('complementary')
    expect(panel).toHaveClass('w-40', 'xl:w-48')
    expect(panel).not.toHaveClass('w-24')
  })

  it('renders a row per day with the count', () => {
    renderTimeline(days)
    expect(screen.getByText('Aug 19')).toBeInTheDocument()
    expect(screen.getByText('Aug 18')).toBeInTheDocument()
    expect(screen.getByText('Jul 30')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('inserts a month divider when the month changes', () => {
    renderTimeline(days)
    expect(screen.getByText('Aug 2026')).toBeInTheDocument()
    expect(screen.getByText('Jul 2026')).toBeInTheDocument()
  })

  it('does not repeat a month divider within the same month', () => {
    renderTimeline(days)
    expect(screen.getAllByText('Aug 2026')).toHaveLength(1)
  })

  it('shows an empty state when there are no days', () => {
    renderTimeline([])
    expect(screen.getByText('No jobs yet')).toBeInTheDocument()
  })

  it('shows the apply count in parenthesis when positive', () => {
    renderTimeline(days)
    expect(screen.getByText('(2 apply)')).toBeInTheDocument()
    expect(screen.queryByText('(0 apply)')).not.toBeInTheDocument()
  })

  it('shows guidance tooltip on row hover', async () => {
    const user = userEvent.setup()
    renderTimeline(days)
    await user.hover(screen.getByText('Aug 19'))
    expect(
      await screen.findByText(/2 of 3 jobs added Aug 19 have been applied to/),
    ).toBeInTheDocument()
  })

  it('shows the no-apply guidance when the day has none', async () => {
    const user = userEvent.setup()
    renderTimeline(days)
    await user.hover(screen.getByText('Aug 18'))
    expect(
      await screen.findByText(/Nothing applied from Aug 18 yet/),
    ).toBeInTheDocument()
  })
})
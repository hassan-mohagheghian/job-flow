import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SkillRow } from './SkillRow'
import type { SkillListItem } from '@/entities/skill/types'

function makeSkill(overrides: Partial<SkillListItem> = {}): SkillListItem {
  return {
    id: 1,
    name: 'Kubernetes',
    level: 4,
    roles: 'DevOps engineer, Platform engineer',
    path: '',
    category: 'engineering',
    categories: ['engineering'],
    confidence: 0.85,
    market_relevance: 0.9,
    evidence: null,
    tags: ['containers', 'k8s'],
    aliases: [],
    source_type: 'user_input',
    mention_count: 0,
    pinned: false,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function renderRow(skill: SkillListItem, overrides: Record<string, unknown> = {}) {
  const props = {
    skill,
    onViewDetails: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  }
  return render(<SkillRow {...(props as any)} />)
}

describe('SkillRow', () => {
  it('renders name, category, level and roles', () => {
    renderRow(makeSkill())

    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText('engineering')).toBeInTheDocument()
    expect(screen.getByText('Lv.4')).toBeInTheDocument()
    expect(screen.getByText(/DevOps engineer/)).toBeInTheDocument()
  })

  it('renders every category badge for a multi-category skill', () => {
    renderRow(makeSkill({ categories: ['technical', 'engineering', 'domain'] }))

    expect(screen.getByText('technical')).toBeInTheDocument()
    expect(screen.getByText('engineering')).toBeInTheDocument()
    expect(screen.getByText('domain')).toBeInTheDocument()
  })

  it('falls back to the primary category when categories is empty', () => {
    renderRow(makeSkill({ category: 'career', categories: [] }))
    expect(screen.getByText('career')).toBeInTheDocument()
  })

  it('renders no category badges when neither category nor categories exist', () => {
    renderRow(makeSkill({ category: '', categories: [] }))
    expect(screen.queryByText('engineering')).not.toBeInTheDocument()
  })

  it('renders confidence and demand percentages', () => {
    renderRow(makeSkill())
    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('renders em dashes when confidence and demand are absent', () => {
    renderRow(makeSkill({ confidence: null, market_relevance: null }))
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('shows the alias badge when aliases exist', () => {
    renderRow(makeSkill({ aliases: ['K8s'] }))
    expect(screen.getByText('1 alias')).toBeInTheDocument()
  })

  it('shows an AI origin badge for ai_generated skills', () => {
    renderRow(makeSkill({ source_type: 'ai_generated' }))
    expect(screen.getByText('AI')).toBeInTheDocument()
  })

  it('shows a Manual origin badge for user_input skills', () => {
    renderRow(makeSkill({ source_type: 'user_input' }))
    expect(screen.getByText('Manual')).toBeInTheDocument()
  })

  it('shows the mention count', () => {
    renderRow(makeSkill({ mention_count: 7 }))
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('shows zero mentions', () => {
    renderRow(makeSkill({ mention_count: 0 }))
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('calls onViewDetails on row click', () => {
    const onViewDetails = vi.fn()
    render(
      <SkillRow
        skill={makeSkill()}
        onViewDetails={onViewDetails}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onBreakDown={vi.fn()}
        onMerge={vi.fn()}
      />
    )
    screen.getByText('Kubernetes').click()
    expect(onViewDetails).toHaveBeenCalledWith(1)
  })
})

describe('SkillRow select column', () => {
  it('renders no checkbox when the select column is off', () => {
    renderRow(makeSkill())
    expect(screen.queryByLabelText('Select Kubernetes')).not.toBeInTheDocument()
  })

  it('renders an unchecked checkbox when the select column is shown', () => {
    renderRow(makeSkill(), { showSelectColumn: true })
    const checkbox = screen.getByLabelText('Select Kubernetes')
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).not.toBeChecked()
  })

  it('renders a checked checkbox when selected', () => {
    renderRow(makeSkill(), { showSelectColumn: true, selected: true })
    expect(screen.getByLabelText('Select Kubernetes')).toBeChecked()
  })

  it('toggles selection and stops row navigation', () => {
    const onToggleSelect = vi.fn()
    const onViewDetails = vi.fn()
    renderRow(makeSkill(), { showSelectColumn: true, onToggleSelect, onViewDetails })

    fireEvent.click(screen.getByLabelText('Select Kubernetes'))

    expect(onToggleSelect).toHaveBeenCalledWith(1)
    expect(onViewDetails).not.toHaveBeenCalled()
  })
})

describe('SkillRow row-number column', () => {
  it('renders no row number when the column is off', () => {
    renderRow(makeSkill())
    expect(screen.queryByText('7')).not.toBeInTheDocument()
  })

  it('renders the row number when the column is shown', () => {
    renderRow(makeSkill(), { showRowNumberColumn: true, rowNumber: 7 })
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('renders nothing for an absent row number', () => {
    renderRow(makeSkill(), { showRowNumberColumn: true })
    expect(screen.queryByText('1')).not.toBeInTheDocument()
  })})

describe('SkillRow hover actions', () => {
  it('wraps the actions in a hover-revealed overlay (hidden by default)', () => {
    const { container } = renderRow(makeSkill())
    const overlay = container.querySelector('[class*="group-hover:opacity-100"]')
    expect(overlay).not.toBeNull()
    expect(overlay?.classList.contains('opacity-0')).toBe(true)
  })

  it('calls the delete handler and does not open details when an action is clicked', () => {
    const onDelete = vi.fn()
    const onViewDetails = vi.fn()
    renderRow(makeSkill(), { onDelete, onViewDetails })

    fireEvent.click(screen.getByLabelText('Delete'))

    expect(onDelete).toHaveBeenCalled()
    expect(onViewDetails).not.toHaveBeenCalled()
  })
})

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SkillDetailDrawer } from './SkillDetailDrawer'
import type { SkillListItem, SkillReferencedJobs } from '@/entities/skill/types'

vi.mock('@/entities/skill/hooks', () => ({
  useSkillReferencedJobs: (skillId: number | null) => ({
    data: skillId != null ? (mockReferencedJobs as SkillReferencedJobs) : null,
    isLoading: false,
    isError: false,
  }),
  useAddSkillNoteMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSkillNoteMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useAddSkillLinkMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSkillLinkMutation: () => ({ mutate: vi.fn(), isPending: false }),
}))

let mockReferencedJobs: SkillReferencedJobs = { jobs: [], total: 0 }

function makeSkill(overrides: Partial<SkillListItem> = {}): SkillListItem {
  return {
    id: 1,
    name: 'Kubernetes',
    level: 4,
    roles: 'DevOps engineer',
    path: '',
    category: 'engineering',
    categories: ['engineering', 'infrastructure'],
    confidence: 0.85,
    market_relevance: 0.9,
    evidence: null,
    tags: [],
    aliases: [],
    source_type: 'user_input',
    mention_count: 0,
    pinned: false,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function renderDrawer(skill: SkillListItem, onOpenJob?: () => void, onTogglePinned?: (id: number, pinned: boolean) => void) {
  return render(
    <SkillDetailDrawer
      skillId={skill.id}
      skill={skill}
      onOpenChange={vi.fn()}
      onEdit={vi.fn()}
      onDelete={vi.fn()}
      onTogglePinned={onTogglePinned}
      onBreakDown={vi.fn()}
      onOpenJob={onOpenJob}
    />
  )
}

describe('SkillDetailDrawer', () => {
  it('shows a dedicated Categories section with every category badge', () => {
    renderDrawer(makeSkill())

    expect(screen.getByText('Categories')).toBeInTheDocument()
    expect(screen.getByText('engineering')).toBeInTheDocument()
    expect(screen.getByText('infrastructure')).toBeInTheDocument()
  })

  it('hides the Categories section when the skill has no categories', () => {
    renderDrawer(makeSkill({ category: '', categories: [] }))
    expect(screen.queryByText('Categories')).not.toBeInTheDocument()
  })

  it('shows the count of referenced jobs in the section header', () => {
    mockReferencedJobs = {
      total: 2,
      jobs: [
        { id: 'j1', title: 'Platform Engineer', company: 'Acme', location: 'Berlin', fit_score: 8, success_score: 7, overall_score: 9, pinned: false, status: 'completed', created_at: null },
        { id: 'j2', title: 'SRE Engineer', company: 'Beta', location: 'Munich', fit_score: 6, success_score: 8, overall_score: 7, pinned: false, status: 'completed', created_at: null },
      ],
    }
    renderDrawer(makeSkill())

    expect(screen.getByText('Referenced Jobs (2)')).toBeInTheDocument()
  })

  it('renders each referenced job row with its title', () => {
    mockReferencedJobs = {
      total: 1,
      jobs: [
        { id: 'j1', title: 'Platform Engineer', company: 'Acme', location: 'Berlin', fit_score: 8, success_score: 7, overall_score: 9, pinned: false, status: 'completed', created_at: null },
      ],
    }
    renderDrawer(makeSkill())

    expect(screen.getByText('Platform Engineer')).toBeInTheDocument()
  })

  it('calls onOpenJob when a job row is clicked', () => {
    mockReferencedJobs = {
      total: 1,
      jobs: [
        { id: 'j1', title: 'Platform Engineer', company: 'Acme', location: 'Berlin', fit_score: null, success_score: null, overall_score: null, pinned: false, status: 'completed', created_at: null },
      ],
    }
    const onOpenJob = vi.fn()
    renderDrawer(makeSkill(), onOpenJob)

    fireEvent.click(screen.getByText('Platform Engineer'))
    expect(onOpenJob).toHaveBeenCalledWith('j1')
  })

  it('shows an empty state when no jobs reference the skill', () => {
    mockReferencedJobs = { jobs: [], total: 0 }
    const skill = makeSkill({ id: 99 })
    render(
      <SkillDetailDrawer
        skillId={skill.id}
        skill={skill}
        onOpenChange={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onBreakDown={vi.fn()}
      />
    )
    expect(screen.getByText('Referenced Jobs (0)')).toBeInTheDocument()
    expect(
      screen.getByText('No jobs reference this skill yet.')
    ).toBeInTheDocument()
  })
})

describe('SkillDetailDrawer pinned', () => {
  it('renders the pin button with the skill pinned state', () => {
    renderDrawer(makeSkill({ pinned: true }), vi.fn(), vi.fn())
    expect(screen.getByLabelText('Unpin skill')).toBeInTheDocument()
  })

  it('calls onTogglePinned with the toggled state', () => {
    const onTogglePinned = vi.fn()
    renderDrawer(makeSkill(), vi.fn(), onTogglePinned)

    fireEvent.click(screen.getByLabelText('Pin skill for attention'))
    expect(onTogglePinned).toHaveBeenCalledWith(1, true)
  })

  it('does not render the pin button without an onTogglePinned handler', () => {
    renderDrawer(makeSkill())
    expect(screen.queryByLabelText('Pin skill for attention')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Unpin skill')).not.toBeInTheDocument()
  })
})
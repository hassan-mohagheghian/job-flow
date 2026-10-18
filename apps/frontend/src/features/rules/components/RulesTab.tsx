import { useState } from 'react'
import { PencilSimple, Trash, Plus, ArrowUp, ArrowDown, Target, DotsSixVertical, Users, Buildings, Briefcase, Handshake } from '@phosphor-icons/react'
import { cn } from '@/shared/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'
import { Button } from '@/shared/ui/button'
import { Badge } from '@/shared/ui/badge'
import { Switch } from '@/shared/ui/switch'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import RuleFormDrawer from './RuleFormDrawer'
import { AUTH_TOKEN_KEY, API_BASE } from '@/shared/config/constants'

const API = '/api'

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  const token = localStorage.getItem(AUTH_TOKEN_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const SCOPE_CONFIG = {
  SHARED: { label: 'Shared', color: 'bg-purple-500/15 text-purple-500 border-purple-500/30', icon: <Users className="w-4 h-4" />, header: 'text-purple-500', headerBg: 'bg-purple-500/5', headerBorder: 'border-purple-500/20', desc: 'Applied to all entity types' },
  JOB: { label: 'Job', color: 'bg-blue-500/15 text-blue-500 border-blue-500/30', icon: <Briefcase className="w-4 h-4" />, header: 'text-blue-500', headerBg: 'bg-blue-500/5', headerBorder: 'border-blue-500/20', desc: 'Applied only to job scoring' },
  COMPANY_PRODUCT: { label: 'Product Company', color: 'bg-green-500/15 text-green-500 border-green-500/30', icon: <Buildings className="w-4 h-4" />, header: 'text-green-500', headerBg: 'bg-green-500/5', headerBorder: 'border-green-500/20', desc: 'Applied to product/engineering companies' },
  COMPANY_RECRUITING: { label: 'Recruiting', color: 'bg-orange-500/15 text-orange-500 border-orange-500/30', icon: <Handshake className="w-4 h-4" />, header: 'text-orange-500', headerBg: 'bg-orange-500/5', headerBorder: 'border-orange-500/20', desc: 'Applied to recruiting/staffing companies' },
}

const FILTER_TABS = [
  { id: 'all', label: 'All' },
  { id: 'SHARED', label: 'Shared' },
  { id: 'JOB', label: 'Jobs' },
  { id: 'COMPANY_PRODUCT', label: 'Product Company' },
  { id: 'COMPANY_RECRUITING', label: 'Recruiting' },
]

function PriorityBadge({ p }) {
  if (p >= 90) return <Badge className="text-2xs px-1 h-3.5 bg-red-500/15 text-red-500 border-red-500/30 shrink-0">Critical</Badge>
  if (p >= 75) return <Badge className="text-2xs px-1 h-3.5 bg-orange-500/15 text-orange-500 border-orange-500/30 shrink-0">High</Badge>
  if (p >= 50) return <Badge variant="secondary" className="text-2xs px-1 h-3.5 shrink-0">Med</Badge>
  return <Badge variant="outline" className="text-2xs px-1 h-3.5 shrink-0">Low</Badge>
}

function ScopeBadge({ scope }) {
  const config = SCOPE_CONFIG[scope] || SCOPE_CONFIG.SHARED
  return <Badge variant="outline" className={cn("text-3xs px-0.5 h-2.5 shrink-0", config.color)}>{config.label}</Badge>
}

function SortableRule({ pref, onOpenEdit, onToggle, onDelete, onMoveUp, onMoveDown }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: pref.id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : undefined,
    opacity: isDragging ? 0.8 : undefined,
  }

  return (
    <div ref={setNodeRef} style={style} className={cn("rounded-lg transition hover:bg-muted/50 group", !pref.enabled && "opacity-40", isDragging && "ring-2 ring-primary/30 shadow-lg")}>
      <div className="flex items-start gap-1.5 p-1.5">
        <div {...attributes} {...listeners} className="shrink-0 mt-0.5 cursor-grab active:cursor-grabbing text-muted-foreground/50 hover:text-muted-foreground transition">
          <DotsSixVertical className="w-3 h-3" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-xs font-semibold truncate">{pref.key}</span>
            <Badge variant="outline" className="text-3xs px-0.5 h-2.5 shrink-0">{pref.category}</Badge>
            <ScopeBadge scope={pref.scope} />
            <PriorityBadge p={pref.priority} />
            <span className="text-2xs text-muted-foreground">w:{pref.priority}</span>
            <div className="flex items-center gap-0.5 ml-auto shrink-0 opacity-0 group-hover:opacity-100 transition">
              <Switch checked={!!pref.enabled} onCheckedChange={(c) => onToggle(pref.id, c)} className="scale-75" title="Enable/Disable" />
              <Button variant="ghost" size="icon" className="h-4 w-4" onClick={() => onMoveUp(pref.id)} title="Move up"><ArrowUp className="w-2 h-2" /></Button>
              <Button variant="ghost" size="icon" className="h-4 w-4" onClick={() => onMoveDown(pref.id)} title="Move down"><ArrowDown className="w-2 h-2" /></Button>
              <Button variant="ghost" size="icon" className="h-4 w-4" onClick={() => onOpenEdit(pref)} title="Edit"><PencilSimple className="w-2 h-2" /></Button>
              <Button variant="ghost" size="icon" className="h-4 w-4 text-destructive hover:text-destructive" onClick={() => onDelete(pref.id)} title="Delete"><Trash className="w-2 h-2" /></Button>
            </div>
          </div>
          <div className="text-2xs text-muted-foreground mt-0.5 ml-4">{pref.value}</div>
          {pref.description && <div className="text-2xs text-muted-foreground/60 mt-0.5 ml-4 italic">{pref.description}</div>}
        </div>
      </div>
    </div>
  )
}

function RuleColumn({ scope, prefs, onOpenAdd, onOpenEdit, onToggle, onDelete, onPriority, onReorder }) {
  const meta = SCOPE_CONFIG[scope]
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))
  const ids = prefs.map(p => p.id)

  const handleMoveUp = (id) => {
    const idx = prefs.findIndex(p => p.id === id)
    if (idx <= 0) return
    onPriority(id, Math.min(prefs[idx - 1].priority + 1, 100))
  }

  const handleMoveDown = (id) => {
    const idx = prefs.findIndex(p => p.id === id)
    if (idx === -1 || idx >= prefs.length - 1) return
    onPriority(id, Math.max(prefs[idx + 1].priority - 1, 0))
  }

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = prefs.findIndex(p => p.id === active.id)
    const newIndex = prefs.findIndex(p => p.id === over.id)
    const reordered = arrayMove(prefs, oldIndex, newIndex)
    onReorder(scope, reordered)
  }

  return (
    <div className="flex flex-col min-w-0">
      <div className={cn("group/header flex items-center gap-2 px-3 py-2 rounded-t-lg border border-b-0", meta.headerBg, meta.headerBorder)}>
        <span className={meta.header}>{meta.icon}</span>
        <span className={cn("text-sm font-bold", meta.header)}>{meta.label} Rules</span>
        <Badge variant="secondary" className="text-2xs ml-auto">{prefs.filter(p => p.enabled).length}/{prefs.length}</Badge>
      </div>
      <div className={cn("rounded-b-lg border p-2 space-y-0.5 max-h-[600px] overflow-y-auto", meta.headerBorder)}>
        <div className="text-2xs text-muted-foreground mb-1">{meta.desc}</div>
        <Button variant="ghost" size="sm" className="h-6 text-2xs gap-0.5 text-muted-foreground w-full justify-start" onClick={() => onOpenAdd(scope)}>
          <Plus className="w-2.5 h-2.5" /> Add rule
        </Button>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={ids} strategy={verticalListSortingStrategy}>
            {prefs.map((pref) => (
              <SortableRule key={pref.id} pref={pref}
                onOpenEdit={onOpenEdit}
                onToggle={onToggle} onDelete={onDelete} onMoveUp={handleMoveUp} onMoveDown={handleMoveDown} />
            ))}
          </SortableContext>
        </DndContext>
      </div>
    </div>
  )
}

export default function RulesTab({ rules, onUpdate }) {
  const [form, setForm] = useState<{ open: boolean; id: string | null; initial: any }>({ open: false, id: null, initial: null })
  const [filter, setFilter] = useState('all')

  const api = async (method, path, body?) => {
    await fetch(`${API}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: body ? JSON.stringify(body) : undefined,
    })
    onUpdate()
  }

  const handleSave = async (id, form) => { await api('PUT', `/rules/${id}`, { value: form.value, description: form.description, scope: form.scope, priority: form.priority }) }
  const handleToggle = async (id, enabled) => api('PUT', `/rules/${id}`, { enabled: enabled ? 1 : 0 })
  const handleDelete = async (id) => api('DELETE', `/rules/${id}`)
  const handleAdd = async (form) => { await api('POST', '/rules', { rules: [{ ...form, rule_type: form.scope === 'SHARED' ? 'shared' : form.scope === 'JOB' ? 'job' : form.scope === 'COMPANY_PRODUCT' ? 'company' : 'recruiter' }] }) }
  const handlePriority = async (id, priority) => api('PUT', `/rules/${id}`, { priority })

  const openAdd = (scope) => {
    setForm({ open: true, id: null, initial: { category: 'fit', scope: scope, key: '', value: '', description: '', priority: 50 } })
  }

  const openEdit = (rule) => {
    setForm({ open: true, id: rule.id, initial: { category: rule.category, scope: rule.scope, key: rule.key, value: rule.value, description: rule.description, priority: rule.priority } })
  }

  const handleFormSave = async (values) => {
    if (form.id) await handleSave(form.id, values)
    else await handleAdd(values)
    setForm((f) => ({ ...f, open: false }))
  }

  const handleReorder = async (scope, reordered) => {
    const total = reordered.length
    const updates = reordered.map((rule, i) => {
      const newPriority = Math.max(1, Math.round(100 - (i / Math.max(total - 1, 1)) * 99))
      return api('PUT', `/rules/${rule.id}`, { priority: newPriority })
    })
    await Promise.all(updates)
  }

  if (!rules) return <div className="text-center py-12 text-muted-foreground">Loading rules...</div>

  // Group rules by scope
  const allRules = []
  const scopeGroups = {}
  for (const [scope, items] of Object.entries(rules)) {
    const sorted = (Array.isArray(items) ? items : []).sort((a, b) => b.priority - a.priority)
    scopeGroups[scope] = sorted
    allRules.push(...sorted)
  }

  const total = allRules.length
  const enabled = allRules.filter(r => r.enabled).length

  // Filter rules based on active filter
  const getFilteredScopes = () => {
    if (filter === 'all') return Object.keys(SCOPE_CONFIG)
    return [filter]
  }

  const filteredScopes = getFilteredScopes().filter(s => scopeGroups[s]?.length > 0)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold">Scoring Rules</h2>
          <p className="text-xs text-muted-foreground">{enabled}/{total} active — Shared rules apply to all entity types</p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-1">
        {FILTER_TABS.map(tab => {
          const count = tab.id === 'all' ? total : (scopeGroups[tab.id]?.length || 0)
          return (
            <Button
              key={tab.id}
              variant={filter === tab.id ? 'default' : 'outline'}
              size="sm"
              className={cn("h-6 text-2xs gap-1", filter === tab.id && "bg-primary text-primary-foreground")}
              onClick={() => setFilter(tab.id)}
            >
              {tab.label}
              <span className="text-2xs opacity-70">({count})</span>
            </Button>
          )
        })}
      </div>

      {/* Rule columns, or the empty state when no scope matches the filter */}
      {filteredScopes.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            <Target className="w-5 h-5 text-muted-foreground" />
          </div>
          <p className="text-sm font-semibold">{total === 0 ? 'No scoring rules yet' : 'No rules in this scope yet'}</p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
            {total === 0
              ? 'Rules weight how jobs and companies are scored. Add your first rule to tune your matches.'
              : 'This scope has no rules yet — add one to apply it to scoring.'}
          </p>
          <Button size="sm" className="mt-4 h-7 text-xs gap-1" onClick={() => openAdd(filter === 'all' ? 'SHARED' : filter)}>
            <Plus className="w-3 h-3" /> Add rule
          </Button>
        </div>
      ) : (
        <div className={cn("gap-3", filteredScopes.length <= 3 ? "grid grid-cols-3" : filteredScopes.length <= 4 ? "grid grid-cols-4" : "grid grid-cols-3")}>
          {filteredScopes.map(scope => (
            <RuleColumn key={scope} scope={scope} prefs={scopeGroups[scope] || []}
              onOpenAdd={openAdd} onOpenEdit={openEdit}
              onToggle={handleToggle} onDelete={handleDelete} onPriority={handlePriority} onReorder={handleReorder} />
          ))}
        </div>
      )}

      <RuleFormDrawer
        key={form.id || 'new'}
        open={form.open}
        onOpenChange={(open) => setForm((f) => ({ ...f, open }))}
        title={form.id ? 'Edit Rule' : 'Add Rule'}
        initial={form.initial}
        onSave={handleFormSave}
      />
    </div>
  )
}

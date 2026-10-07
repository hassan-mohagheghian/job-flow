import {
  Briefcase,
  Buildings,
  TrayArrowDown,
  MapPin,
  TreeStructure,
  Gear,
  Brain,
  UserCircle,
  Signpost,
  TextT,
  type Icon,
} from '@phosphor-icons/react'

export interface NavChild {
  id: string
  label: string
}

export interface NavItem {
  id: string
  label: string
  icon: Icon
  children?: NavChild[]
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'jobs', label: 'Jobs', icon: Briefcase },
  { id: 'opportunities', label: 'Opportunities', icon: TrayArrowDown },
  { id: 'companies', label: 'Companies', icon: Buildings },
  { id: 'cities', label: 'Cities', icon: MapPin },
  { id: 'skills', label: 'Skills', icon: TreeStructure },
  { id: 'candidate', label: 'Candidate', icon: UserCircle },
  { id: 'roadmaps', label: 'Roadmaps', icon: Signpost },
  { id: 'placeholders', label: 'Placeholders', icon: TextT },
  { id: 'rules', label: 'Rules', icon: Gear },
  {
    id: 'ai',
    label: 'AI',
    icon: Brain,
    children: [{ id: 'llm-configurations', label: 'LLM Configurations' }],
  },
]

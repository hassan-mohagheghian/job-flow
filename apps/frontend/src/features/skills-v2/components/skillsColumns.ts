export const SKILL_GRID_TEMPLATE = 'minmax(160px, 2fr) minmax(150px, 1.6fr) 70px minmax(140px, 1.4fr) 90px 90px 80px 90px'

export const LEADING_COLUMN_WIDTH = '44px'

export function buildSkillGridTemplate(showRowNumber: boolean, showSelect: boolean): string {
  const leading: string[] = []
  if (showRowNumber) leading.push(LEADING_COLUMN_WIDTH)
  if (showSelect) leading.push(LEADING_COLUMN_WIDTH)
  return leading.length ? `${leading.join(' ')} ${SKILL_GRID_TEMPLATE}` : SKILL_GRID_TEMPLATE
}

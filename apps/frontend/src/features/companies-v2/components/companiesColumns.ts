export const COMPANY_GRID_TEMPLATE = 'minmax(180px, 2fr) minmax(120px, 1.3fr) 130px minmax(120px, 1.3fr) 90px 60px 150px 110px 80px 80px'

export const LEADING_COLUMN_WIDTH = '44px'

export function buildCompanyGridTemplate(showRowNumber: boolean): string {
  const leading: string[] = []
  if (showRowNumber) leading.push(LEADING_COLUMN_WIDTH)
  return leading.length ? `${leading.join(' ')} ${COMPANY_GRID_TEMPLATE}` : COMPANY_GRID_TEMPLATE
}

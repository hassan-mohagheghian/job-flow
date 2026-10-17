'use client'

import dynamic from 'next/dynamic'

const DashboardPageWidget = dynamic(() => import('@/widgets/dashboard-page').then(m => m.default || m), {
  loading: () => <div className="flex items-center justify-center h-64 text-muted-foreground">Loading dashboard...</div>,
  ssr: false,
})

export default function DashboardRoute() {
  return <DashboardPageWidget />
}

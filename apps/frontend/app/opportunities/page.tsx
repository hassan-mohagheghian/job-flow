'use client'

import dynamic from 'next/dynamic'

const OpportunitiesPageWidget = dynamic(() => import('@/widgets/opportunities-page').then(m => m.default || m), {
  loading: () => <div className="flex items-center justify-center h-64 text-muted-foreground">Loading opportunities...</div>,
  ssr: false,
})

export default function OpportunitiesRoute() {
  return <OpportunitiesPageWidget />
}

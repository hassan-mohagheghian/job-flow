import { PushPin } from '@phosphor-icons/react'
import { Button } from '@/shared/ui/button'
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/shared/ui/tooltip'
import { cn } from '@/shared/lib/utils'

interface PinButtonProps {
  pinned: boolean
  onToggle: () => void
  entityLabel?: string
  className?: string
}

export function PinButton({ pinned, onToggle, entityLabel, className }: PinButtonProps) {
  const label = entityLabel ? `Pin ${entityLabel} for attention` : 'Pin for attention'
  const unpinLabel = entityLabel ? `Unpin ${entityLabel}` : 'Unpin'
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={cn('h-6 w-6 p-0', className)}
            onClick={onToggle}
            aria-label={pinned ? unpinLabel : label}
            aria-pressed={pinned}
          >
            <PushPin
              className={cn('w-3.5 h-3.5', pinned ? 'text-primary' : 'text-muted-foreground')}
              weight={pinned ? 'fill' : 'regular'}
            />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {pinned ? unpinLabel : label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

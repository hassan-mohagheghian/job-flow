'use client'

import { useEffect, useState } from 'react'
import { CalendarBlank, CaretLeft, CaretRight } from '@phosphor-icons/react'
import { Button } from '@/shared/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover'
import { cn } from '@/shared/lib/utils'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

export function toISODate(year: number, month0: number, day: number): string {
  return `${year}-${pad(month0 + 1)}-${pad(day)}`
}

export function parseISODate(value: string): { year: number; month: number; day: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec((value || '').trim())
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2]) - 1
  const day = Number(match[3])
  if (month < 0 || month > 11) return null
  const dim = new Date(year, month + 1, 0).getDate()
  if (day < 1 || day > dim) return null
  return { year, month, day }
}

function daysInMonth(year: number, month0: number): number {
  return new Date(year, month0 + 1, 0).getDate()
}

/** Monday-first offset of the 1st of the month (0 = Monday … 6 = Sunday). */
function leadingBlanks(year: number, month0: number): number {
  return (new Date(year, month0, 1).getDay() + 6) % 7
}

interface DatePickerProps {
  value: string
  onChange: (isoDate: string) => void
  label?: string
  placeholder?: string
}

export function DatePicker({ value, onChange, label = 'Date', placeholder = 'Pick a date' }: DatePickerProps) {
  const [open, setOpen] = useState(false)
  const today = new Date()
  const [view, setView] = useState(() => {
    const parsed = parseISODate(value)
    return { year: parsed?.year ?? today.getFullYear(), month: parsed?.month ?? today.getMonth() }
  })

  // When the popup opens, show the month of the current value (or today).
  useEffect(() => {
    if (open) {
      const parsed = parseISODate(value)
      const now = new Date()
      setView({
        year: parsed?.year ?? now.getFullYear(),
        month: parsed?.month ?? now.getMonth(),
      })
    }
  }, [open, value])

  const selected = parseISODate(value)

  const goMonth = (delta: number) => {
    setView((v) => {
      const next = new Date(v.year, v.month + delta, 1)
      return { year: next.getFullYear(), month: next.getMonth() }
    })
  }

  const blanks = leadingBlanks(view.year, view.month)
  const total = daysInMonth(view.year, view.month)
  const cells: (number | null)[] = [
    ...Array<null>(blanks).fill(null),
    ...Array.from({ length: total }, (_, i) => i + 1),
  ]

  return (
    <div>
      <span className="block text-xs font-medium mb-1">{label}</span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            aria-label={`${label} picker`}
            className={cn('w-full justify-start gap-2 font-normal', !value && 'text-muted-foreground')}
          >
            <CalendarBlank className="w-4 h-4 shrink-0" aria-hidden />
            <span>{value || placeholder}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-3" align="start" aria-label={`${label} calendar`}>
          <div className="flex items-center justify-between mb-2">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Previous month"
              className="h-7 w-7"
              onClick={() => goMonth(-1)}
            >
              <CaretLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm font-semibold" aria-live="polite">
              {MONTH_NAMES[view.month]} {view.year}
            </span>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Next month"
              className="h-7 w-7"
              onClick={() => goMonth(1)}
            >
              <CaretRight className="w-4 h-4" />
            </Button>
          </div>
          <div className="grid grid-cols-7 gap-0.5 text-center">
            {WEEKDAYS.map((d) => (
              <span key={d} className="text-2xs font-semibold uppercase text-muted-foreground py-1">
                {d}
              </span>
            ))}
            {cells.map((day, i) =>
              day === null ? (
                <span key={`blank-${i}`} />
              ) : (
                <button
                  key={day}
                  type="button"
                  aria-label={`${toISODate(view.year, view.month, day)}`}
                  aria-pressed={selected?.year === view.year && selected?.month === view.month && selected?.day === day}
                  onClick={() => {
                    onChange(toISODate(view.year, view.month, day))
                    setOpen(false)
                  }}
                  className={cn(
                    'h-8 w-8 rounded-md text-xs hover:bg-muted mx-auto',
                    selected?.year === view.year &&
                      selected?.month === view.month &&
                      selected?.day === day &&
                      'bg-primary text-primary-foreground hover:bg-primary',
                  )}
                >
                  {day}
                </button>
              ),
            )}
          </div>
          {value && (
            <Button
              variant="ghost"
              size="sm"
              className="w-full mt-2"
              onClick={() => {
                onChange('')
                setOpen(false)
              }}
            >
              Clear
            </Button>
          )}
        </PopoverContent>
      </Popover>
    </div>
  )
}

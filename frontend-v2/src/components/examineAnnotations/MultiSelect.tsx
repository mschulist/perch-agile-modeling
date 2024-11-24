'use client'

import { useState, useRef, useCallback } from 'react'
import { X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  Command,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Command as CommandPrimitive } from 'cmdk'

interface MultiSelectProps {
  options: string[]
}

export function MultiSelect({ options }: MultiSelectProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [inputValue, setInputValue] = useState('')

  const handleUnselect = useCallback((value: string) => {
    setSelected((prev) => prev.filter((s) => s !== value))
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const input = inputRef.current
      if (input) {
        if (e.key === 'Enter' && inputValue) {
          if (!selected.includes(inputValue)) {
            setSelected((prev) => [...prev, inputValue])
            setInputValue('')
          }
          e.preventDefault()
        } else if (
          (e.key === 'Delete' || e.key === 'Backspace') &&
          input.value === ''
        ) {
          setSelected((prev) => {
            const newSelected = [...prev]
            newSelected.pop()
            return newSelected
          })
        } else if (e.key === 'Escape') {
          input.blur()
        }
      }
    },
    [inputValue, selected]
  )

  const filteredOptions = options.filter(
    (option) =>
      option.toLowerCase().includes(inputValue.toLowerCase()) &&
      !selected.includes(option)
  )

  return (
    <Command
      onKeyDown={handleKeyDown}
      className='overflow-visible bg-transparent'
    >
      <div className='group rounded-md border border-input px-3 py-2 text-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2'>
        <div className='flex flex-wrap gap-1'>
          {selected.map((value) => (
            <Badge key={value} variant='secondary'>
              {value}
              <button
                className='ml-1 rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2'
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleUnselect(value)
                  }
                }}
                onMouseDown={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                }}
                onClick={() => handleUnselect(value)}
              >
                <X className='h-3 w-3 text-muted-foreground hover:text-foreground' />
              </button>
            </Badge>
          ))}
          <CommandPrimitive.Input
            ref={inputRef}
            value={inputValue}
            onValueChange={setInputValue}
            onBlur={() => setOpen(false)}
            onFocus={() => setOpen(true)}
            placeholder='Select or type values...'
            className='ml-2 flex-1 bg-transparent outline-none placeholder:text-muted-foreground'
          />
        </div>
      </div>
      {open && (
        <div className='relative mt-2'>
          <CommandList>
            <div className='absolute top-0 z-10 w-full rounded-md border bg-popover text-popover-foreground shadow-md outline-none animate-in'>
              <CommandGroup className='h-full overflow-auto'>
                {filteredOptions.map((option) => (
                  <CommandItem
                    key={option}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                    }}
                    onSelect={() => {
                      setSelected((prev) => [...prev, option])
                      setInputValue('')
                    }}
                    className='cursor-pointer'
                  >
                    {option}
                  </CommandItem>
                ))}
                {filteredOptions.length === 0 && (
                  <CommandItem
                    onMouseDown={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                    }}
                    onSelect={() => {
                      if (!selected.includes(inputValue) && inputValue) {
                        setSelected((prev) => [...prev, inputValue])
                        setInputValue('')
                      }
                    }}
                    className='cursor-pointer'
                  >
                    Add "{inputValue}"
                  </CommandItem>
                )}
              </CommandGroup>
            </div>
          </CommandList>
        </div>
      )}
    </Command>
  )
}

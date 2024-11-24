'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
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
  setLabels: (labels: string[]) => void
  labels: string[]
  placeholder: string
  required?: boolean
}

export function MultiSelect({ options, setLabels, labels, placeholder, required }: MultiSelectProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>(labels)
  const [inputValue, setInputValue] = useState('')

  const requireAtLeastOne = required ?? true

  useEffect(() => {
    setLabels(selected)
  }, [selected])

  useEffect(() => {
    setSelected(labels)
  }, [labels])

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
      <div className='group rounded-lg py-2 text-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2'>
        <div className='flex flex-col gap-2'>
          <div className='flex gap-1 flex-wrap'>
            {selected.map((value) => (
              <Badge
                key={value}
                variant='secondary'
                className='rounded-lg py-3 text-lg bg-neutral w-fit'
              >
                {value}
                {(selected.length > 1 || !requireAtLeastOne)&& (
                  <button
                    className='rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2 ml-1'
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
                )}
              </Badge>
            ))}
          </div>
          <CommandPrimitive.Input
            ref={inputRef}
            value={inputValue}
            onValueChange={setInputValue}
            onBlur={() => setOpen(false)}
            onFocus={() => setOpen(true)}
            placeholder={placeholder}
            className='bg-transparent outline-none placeholder:text-muted-foreground input input-bordered'
          />
        </div>
      </div>
      {open && (
        <div className='relative mt-2'>
          <CommandList className='rounded-lg shadow-md'>
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
                  className='cursor-pointer rounded-xl hover:bg-accent hover:text-accent-foreground text-base'
                >
                  {option}
                </CommandItem>
              ))}
              {filteredOptions.length === 0 && inputValue && (
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
                  className='cursor-pointer rounded-md hover:bg-accent hover:text-accent-foreground'
                >
                  Add "{inputValue}"
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </div>
      )}
    </Command>
  )
}

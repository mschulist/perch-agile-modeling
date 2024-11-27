'use client'

import { useState } from 'react'

export function AnnotationSummary({
  annotationSummary,
  setSingleLabel,
}: {
  annotationSummary: Record<string, number>
  setSingleLabel: (label: string) => void
}) {
  const [searchText, setSearchText] = useState('')

  const filteredAnnotationSummary = Object.entries(annotationSummary).filter(
    ([label]) => label.includes(searchText)
  )

  return (
    <div className='flex flex-col items-center gap-4'>
      <h2 className='text-3xl'>Annotation Summary</h2>
      <input
        type='text'
        className='input input-bordered'
        placeholder='Search labels'
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
      />
      <ul className='h-full overflow-y-scroll p-4 bg-base-200 rounded-xl'>
        {filteredAnnotationSummary.map(([label, count]) => (
          <li key={label} className='m-1'>
            <button
              className='text-xl hover:scale-110 transition-transform'
              onClick={() => setSingleLabel(label)}
            >
              {label}: {count}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

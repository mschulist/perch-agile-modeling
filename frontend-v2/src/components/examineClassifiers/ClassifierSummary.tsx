'use client'

import { ClassifiedResult } from '@/models/perch'
import { useState } from 'react'

type ClassifierSummaryProps = {
  classifiedResults: ClassifiedResult[]
  singleLabel: string | null
  setSingleLabel: (label: string | null) => void
}

export function ClassifierSummary({
  classifiedResults,
  singleLabel,
  setSingleLabel,
}: ClassifierSummaryProps) {
  const [searchText, setSearchText] = useState('')

  const classifiedResultsSummary =
    convertClassifiedResultsToSummary(classifiedResults)

  const filteredClassificationSummary = Object.entries(
    classifiedResultsSummary
  ).filter(([label]) => label.includes(searchText))

  return (
    <div className='flex flex-col items-center gap-4'>
      <h2 className='text-3xl'>Classifier Results Summary</h2>
      <input
        type='text'
        className='input input-bordered'
        placeholder='Search labels'
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
      />
      <ul className='h-full overflow-y-scroll p-4 bg-base-200 rounded-xl'>
        {filteredClassificationSummary.map(([label, count]) => (
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

function convertClassifiedResultsToSummary(
  classifiedResults: ClassifiedResult[]
): Record<string, number> {
  const summary: Record<string, number> = {}
  for (const classifiedResult of classifiedResults) {
    if (classifiedResult.label in summary) {
      summary[classifiedResult.label] += 1
    } else {
      summary[classifiedResult.label] = 1
    }
  }
  return summary
}

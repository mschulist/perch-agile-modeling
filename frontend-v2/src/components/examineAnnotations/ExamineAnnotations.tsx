'use client'

import { useState } from 'react'
import { ExamineAnnotationsSummary } from './ExamineAnnotationsSummary'

export function ExamineAnnotations() {
  const [summary, setSummary] = useState<boolean>(true)

  return (
    <div>
      <button className='btn' onClick={() => setSummary(!summary)}>
        {summary ? 'Hide' : 'Show'} Annotation Summary
      </button>
      {summary ? (
        <div className='flex flex-col justify-center w-full items-center'>
          <h2>Annotation Summary</h2>
          <ExamineAnnotationsSummary />
        </div>
      ) : (
        <></>
      )}
    </div>
  )
}

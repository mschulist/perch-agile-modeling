import { PossibleExample } from '@/models/perch'
import { useState } from 'react'

export function AnnotationButtons({
  possibleExample,
  annotateAndGetNextPossibleExample,
}: {
  possibleExample: PossibleExample
  annotateAndGetNextPossibleExample: (labels: string[]) => void
}) {
  const [labels, setLabels] = useState<string>('')
  return (
    <div className='flex flex-col w-full justify-center items-center gap-6'>
      <input
        className='input input-bordered'
        type='text'
        placeholder={possibleExample.target_species}
        onChange={(e) => setLabels(e.target.value)}
      />
      <button
        className='btn btn-primary w-44'
        onClick={() => {
          annotateAndGetNextPossibleExample(labels.split(','))
          setLabels('')
        }}
      >
        Annotate with Labels
      </button>
    </div>
  )
}

import { ClassifiedResult } from '@/models/perch'
import { SingleClassifiedRecording } from './SingleClassifiedRec'

export function SingleLabelClassifiedRecs({
  classifiedResults,
  annotationSummary,
}: {
  classifiedResults: ClassifiedResult[]
  annotationSummary: Record<string, number>
}) {
  return (
    <div className='flex flex-col items-center gap-4'>
      <h2 className='text-3xl'>Annotation Summary</h2>
      <ul className='h-full overflow-y-scroll p-4 bg-base-200 rounded-xl'>
        {classifiedResults.map((classifiedResult, i) => (
          <SingleClassifiedRecording
            key={i}
            classifiedResult={classifiedResult}
            annotationSummary={annotationSummary}
          />
        ))}
      </ul>
    </div>
  )
}

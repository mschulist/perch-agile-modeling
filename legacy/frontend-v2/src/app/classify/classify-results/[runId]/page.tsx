import { ClassifierResults } from '@/components/examineClassifiers/ClassifierResults'

export default async function ClassifyResults({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const runId = parseInt((await params).runId)

  return (
    <div className='flex h-5/6 align-middle justify-center'>
      <ClassifierResults classifyRunId={runId} />
    </div>
  )
}

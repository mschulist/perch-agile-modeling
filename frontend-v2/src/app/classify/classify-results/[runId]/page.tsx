export default async function ClassifyResults({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const runId = (await params).runId

  return (
    <div className='flex justify-center items-center align-middle text-2xl'>
      {runId}
    </div>
  )
}

export function AgileStep({
  number,
  title,
  description,
}: {
  number: number
  title: string
  description: JSX.Element | string
}) {
  return (
    <div className='bg-primary-foreground overflow-hidden shadow rounded-lg'>
      <div className='p-6'>
        <div className='flex items-center'>
          <span className='h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold'>
            {number}
          </span>
          <h3 className='ml-3 text-lg font-medium'>{title}</h3>
        </div>
        <div className='mt-4'>{description}</div>
      </div>
    </div>
  )
}

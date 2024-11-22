export function AnnotationSummary({
  annotationSummary,
  setSingleLabel,
}: {
  annotationSummary: Record<string, number>
  setSingleLabel: (label: string) => void
}) {
  console.log(annotationSummary)
  return (
    <ul>
      {Object.entries(annotationSummary).map(([label, count]) => (
        <li key={label}>
          <button className='text-xl hover:scale-110 transition-transform' onClick={() => setSingleLabel(label)}>
            {label}: {count}
          </button>
        </li>
      ))}
    </ul>
  )
}

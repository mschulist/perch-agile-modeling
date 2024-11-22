export function AnnotationSummary({
  annotationSummary,
}: {
  annotationSummary: Record<string, number>
}) {
  return (
    <ul>
      {Object.entries(annotationSummary).map(([label, count]) => (
        <li key={label}>
          <span>{label}</span>
          <span>{count}</span>
        </li>
      ))}
    </ul>
  )
}

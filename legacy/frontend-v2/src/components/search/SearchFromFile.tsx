export function SearchFromFile({
  setSpeciesCodes,
}: {
  setSpeciesCodes: (speciesCodes: string[]) => void
}) {
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      const codes = text
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
      setSpeciesCodes(codes)
    }
    reader.onerror = (e) => {
      console.error('Error reading file:', e)
    }
    reader.readAsText(file)
  }

  return (
    <input
      type='file'
      accept='.txt'
      onChange={handleFileUpload}
      className='file-input file-input-bordered file-input-primary w-full max-w-xs'
    />
  )
}

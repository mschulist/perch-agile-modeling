import { DualRangeSlider } from '@/components/ui/dual-range-slider'

type LogitRangeSliderProps = {
  logitRanges: Array<[number, number]>
  setLogitRanges: (ranges: Array<[number, number]>) => void
}

export function LogitRangeSlider({
  logitRanges,
  setLogitRanges,
}: LogitRangeSliderProps) {
  const addRange = () => {
    setLogitRanges([...logitRanges, [0, 2]])
  }

  const removeRange = (index: number) => {
    setLogitRanges(logitRanges.filter((_, i) => i !== index))
  }

  const updateRange = (index: number, newRange: [number, number]) => {
    const newLogitRanges = [...logitRanges]
    newLogitRanges[index] = newRange
    setLogitRanges(newLogitRanges)
  }

  return (
    <div>
      {logitRanges.map((range, index) => (
        <div key={index} className='flex items-center gap-6 mb-2'>
          <DualRangeSlider
            min={-5}
            max={5}
            step={0.1}
            value={range}
            onValueChange={(newRange) => {
              if (newRange.length === 2) {
                updateRange(index, newRange as [number, number])
              }
            }}
            label={(value) => value?.toFixed(2)}
          />
          <button
            className='btn btn-error btn-xs'
            onClick={() => removeRange(index)}
          >
            Remove
          </button>
        </div>
      ))}
      <button className='btn btn-primary btn-sm' onClick={addRange}>
        Add Range
      </button>
    </div>
  )
}

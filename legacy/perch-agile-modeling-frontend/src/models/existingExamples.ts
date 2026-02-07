export interface ExistingExamples {
    type: ExampleType
    examples: Example[]
}

export type ExampleType = "searchResults" | "targetRecordings" | "labeledOutputs"

export type Example = {
    class: string
    number: number
}

export type existingLabeledOutput = {
    exampleClass: string
    filename: string
    timestampS: string
    gsuri: string
    audio_url: string
    spec_url?: string
}
export interface ExistingExamples {
    type: ExampleType
    examples: Example[]
}

export type ExampleType = "searchResults" | "targetRecordings" | "labeledOutputs"

export type Example = {
    class: string
    number: number
}

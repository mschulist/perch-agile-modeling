import { Example, ExistingExamples } from "@/models/existingExamples"

export default function ExistingExamplesComponent({
    examples,
}: {
    examples: Example[]
}) {
    return (
        <div className="flex flex-row h-96 overflow-y-scroll">
            <ul className="list-disc pl-4">
                {examples.map((example) => (
                    <li key={example.class + example.number} className="mb-2">
                        {example.class}: {example.number}
                    </li>
                ))}
            </ul>
        </div>
    )
}

import { ExistingExamples } from "@/models/existingExamples"

export default function ExistingExamplesComponent({
    examples,
}: {
    examples: ExistingExamples
}) {
    return (
        <div>
            <h2>Existing Examples</h2>
            <ul>
                {examples.examples.map((example) => (
                    <li key={example.class + example.number}>
                        {example.class} {example.number}
                    </li>
                ))}
            </ul>
        </div>
    )
}

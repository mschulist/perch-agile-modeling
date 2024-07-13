"use client"
import { Example, existingLabeledOutput } from "@/models/existingExamples"
import { useProject } from "./Auth"
import { useState } from "react"
import ExistingLabeledExamples from "./ExistingLabeledExamples"

export default function ExistingExamplesComponent({
    examples,
    exampleType,
    canView = false,
    getExamples,
}: {
    examples: Example[]
    exampleType: string
    canView?: boolean
    getExamples: () => void
}) {
    const [labeledExamples, setLabeledExamples] = useState<
        existingLabeledOutput[]
    >([])

    const examplesClasses = examples.map((example) => example.class)

    const project = useProject()

    async function getLabeledExamples(exampleClass: string) {
        // fetch labeled examples from backend
        fetch("api/getExamplesSingleFolder", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                exampleClass: exampleClass,
                exampleType: exampleType,
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            setLabeledExamples(data.examples)
        })
    }
    console.log(labeledExamples)

    return (
        <div className="flex flex-col justify-center items-center">
            {labeledExamples.length > 0 && (
                <h2 className="text-2xl font-bold py-2 self-center text-orange-300">
                    {labeledExamples[0].exampleClass}
                </h2>
            )}
            <div className="flex flex-row min-w-80">
                <div
                    className={`flex flex-row h-[42rem] overflow-y-scroll min-w-60 m-10`}
                >
                    <ul className="list-disc pl-4">
                        {examples.map((example) => (
                            <li
                                key={example.class + example.number}
                                className={`mb-2 ${
                                    canView
                                        ? "cursor-pointer hover:scale-110 transition-transform duration-50 ease-in-out"
                                        : ""
                                }`}
                                onClick={() =>
                                    getLabeledExamples(example.class)
                                }
                            >
                                {example.class}: {example.number}
                            </li>
                        ))}
                    </ul>
                </div>
                {labeledExamples.length > 0 && (
                    <ExistingLabeledExamples
                        labeledExamples={labeledExamples}
                        exampleClasses={examplesClasses}
                        getExamples={getExamples}
                        getLabeledExamples={getLabeledExamples}
                    />
                )}
            </div>
        </div>
    )
}

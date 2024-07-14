"use client"
import { Example, existingLabeledOutput } from "@/models/existingExamples"
import { useProject } from "./Auth"
import { useState } from "react"
import ExistingLabeledExamples from "./ExistingLabeledExamples"
import { Input } from "./ui/input"

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
    const [filteredExamplesAgg, setFilteredExamplesAgg] =
        useState<Example[]>(examples)

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

    function filterExamples(exampleClass: string) {
        if (exampleClass === "") {
            setFilteredExamplesAgg(examples)
            return
        }
        const filtered = examples.filter((example) =>
            example.class.toLowerCase().startsWith(exampleClass.toLowerCase())
        )
        setFilteredExamplesAgg(filtered)
    }

    return (
        <div className="flex flex-col justify-center items-center">
            {labeledExamples.length > 0 && (
                <h2 className="text-2xl font-bold py-2 self-center text-orange-300 text-center">
                    {labeledExamples[0].exampleClass}
                    <br />
                    {labeledExamples[0].exampleClass === "unknown" && (
                        <span className="text-red-400 text-lg">
                            Note: unknown means no birds present
                        </span>
                    )}
                </h2>
            )}
            <Input
                className="mx-10 mt-4 mb-[-1rem] justify-start self-start w-60"
                placeholder="Filter examples"
                onChange={(e) => filterExamples(e.target.value)}
            />
            <div className="flex flex-row min-w-80">
                <div className="flex flex-row h-[42rem] overflow-y-scroll min-w-60 m-10">
                    <ul className="list-disc pl-4">
                        {filteredExamplesAgg.map((example) => (
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
                                <span
                                    className={
                                        example.class === "unknown"
                                            ? "text-red-400"
                                            : ""
                                    }
                                >
                                    {example.class}: {example.number}
                                </span>
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

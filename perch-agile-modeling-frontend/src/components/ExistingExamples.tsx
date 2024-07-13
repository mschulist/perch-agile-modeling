"use client"
import {
    Example,
    existingLabeledOutput,
} from "@/models/existingExamples"
import { useProject } from "./Auth"
import { useState } from "react"
import Image from "next/image"

export default function ExistingExamplesComponent({
    examples,
    exampleType,
    canView = false,
}: {
    examples: Example[]
    exampleType: string
    canView?: boolean
}) {
    const [labeledExamples, setLabeledExamples] = useState<
        existingLabeledOutput[]
    >([])

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
                <div className={`flex flex-row h-[42rem] overflow-y-scroll min-w-60 m-10`}>
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
                    <div className="flex flex-col m-10 w-full">
                        <ul className="list-disc px-5 h-[42rem] overflow-y-scroll">
                            {labeledExamples.map((example) => (
                                <li
                                    key={`${example.filename}.${example.audio_url}`}
                                >
                                    Filename: {example.filename}
                                    <br />
                                    Timestamp: {example.timestampS} seconds
                                    {example.spec_url && (
                                        <Image
                                            src={example.spec_url}
                                            alt=""
                                            height={600}
                                            width={600}
                                            className="rounded-xl"
                                        />
                                    )}
                                    <br />
                                    <audio
                                        src={example.audio_url}
                                        controls
                                        className="pb-4"
                                    />
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    )
}

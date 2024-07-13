"use client"
import { ExampleType, Example } from "@/models/existingExamples"
import { useState, useEffect } from "react"
import ExistingExamplesComponent from "./ExistingExamples"
import { useProject } from "./Auth"

const EXAMPLE_TYPE: ExampleType = "searchResults"

export default function LabeledOutputsPage() {
    const [targetRecordings, setTargetRecordings] = useState<Example[]>([])

    const project = useProject()

    useEffect(() => {
        if (!project) {
            return
        }
        const getExamples = async () => {
            fetch("api/getExamples", {
                method: "POST",
                body: JSON.stringify({
                    project: project,
                    exampleType: EXAMPLE_TYPE,
                }),
            }).then(async (res) => {
                const data = await res.json()
                if (!data.success) {
                    console.error("Error occurred during fetch:", data.error)
                    return
                }
                console.log(data)
                setTargetRecordings(data.examples)
            })
        }
        getExamples()
    }, [project])

    return (
        <div className="flex flex-col justify-center items-center h-screen">
            {targetRecordings.length > 0 && (
                <div className="flex flex-col">
                    <h2 className="text-2xl font-bold py-2">
                        Existing Search Results
                    </h2>
                    <ExistingExamplesComponent
                        examples={targetRecordings}
                        exampleType={EXAMPLE_TYPE}
                    />
                </div>
            )}
        </div>
    )
}

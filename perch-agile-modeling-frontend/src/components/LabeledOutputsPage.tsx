"use client"
import { Example, ExampleType } from "@/models/existingExamples"
import { useState, useEffect } from "react"
import ExistingExamplesComponent from "./ExistingExamples"
import { useProject } from "./Auth"

const EXAMPLE_TYPE: ExampleType = "labeledOutputs"

export default function LabeledOutputsPage() {
    const [labeledOutputs, setLabeledOutputs] = useState<Example[]>([])

    const project = useProject()

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
            setLabeledOutputs(data.examples)
        })
    }

    useEffect(() => {
        if (!project) {
            return
        }

        getExamples()
    }, [project])

    return (
        <div className="flex flex-col justify-center items-center h-5/6">
            {labeledOutputs.length > 0 && (
                <div className="flex flex-col">
                    <h2 className="text-2xl font-bold py-2 self-center">
                        Existing Labeled Outputs
                    </h2>
                    <ExistingExamplesComponent
                        examples={labeledOutputs}
                        canView={true}
                        exampleType={EXAMPLE_TYPE}
                        getExamples={getExamples}
                    />
                </div>
            )}
        </div>
    )
}

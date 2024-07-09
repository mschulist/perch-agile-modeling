"use client"
import { useCallback, useEffect, useState } from "react"
import ExistingExamplesComponent from "./ExistingExamples"
import { Example, ExistingExamples } from "@/models/existingExamples"
import { get } from "http"

const EXAMPLE_TYPE = "targetRecordings"

export default function TargetRecordings() {
    const [project, setProject] = useState<string>("caples-testing")
    const [targetRecordings, setTargetRecordings] = useState<Example[]>([])

    useEffect(() => {
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
                <ExistingExamplesComponent examples={targetRecordings} />
            )}
        </div>
    )
}

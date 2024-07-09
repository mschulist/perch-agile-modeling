"use client"
import { useState } from "react"
import ExistingExamplesComponent from "./ExistingExamples"
import { Example, ExistingExamples } from "@/models/existingExamples"
import { ConstructionIcon } from "lucide-react"

const EXAMPLE_TYPE = "targetRecordings"

export default function TargetRecordings() {
    const [project, setProject] = useState<string>("caples-testing")
    const [examples, setExamples] = useState<Example[]>([])

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
            setExamples(data.examples)
        })
    }

    return (
        <div className="flex justify-center items-center h-screen">
            <button
                onClick={getExamples}
                className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
                Get Examples
            </button>
            {/* <ExistingExamplesComponent /> */}
        </div>
    )
}

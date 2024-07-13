"use client"
import React, { useEffect, useState } from "react"
import Image from "next/image"
import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import AnnotationButtons from "./AnnotationButtons"
import { useAuth, useProject } from "./Auth"
import { Example } from "@/models/existingExamples"

const voc_types = ["call", "song"]

export default function AnnotateRecordings() {
    const [example, setExample] = useState<precomputedExample | null>(null)
    const [exampleClasses, setExampleClasses] = useState<string[]>([])

    const user = useAuth()
    const project = useProject()

    useEffect(() => {
        // get the next example when first loading the page
        if (!project || !user) {
            return
        }
        fetch("api/getNextExample", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                user: user,
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            setExample(data.example)
        })

        console.log("project", project)

        // get all of the example classes when first loading the page
        fetch("api/getExamples", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                exampleType: "labeledOutputs",
            }),
        }).then(async (res) => {
            console.log(res)
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            const examples: Example[] = data.examples
            setExampleClasses(examples.map((example) => example.class))
        })
    }, [project, user])

    function getNextExample() {
        setExample(null)
        fetch("api/getNextExample", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                user: user,
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            setExample(data.example)
        })
    }

    return (
        <div className="flex self-center py-10 h-full px-16">
            <div className="flex flex-col w-full align-top">
                <Button
                    variant="outline"
                    className="m-2 self-center"
                    onClick={getNextExample}
                >
                    Skip Recording
                </Button>
                {example && (
                    <>
                        <Image
                            src={example.spec_url}
                            alt=""
                            width={500}
                            height={500}
                            className="m-4 rounded-xl self-center"
                        />
                        <audio
                            controls
                            src={example.audio_url}
                            className="m-4 self-center"
                        />
                        <AnnotationButtons
                            example={example}
                            getNextExample={getNextExample}
                            exampleClasses={exampleClasses}
                        />
                    </>
                )}
            </div>
        </div>
    )
}

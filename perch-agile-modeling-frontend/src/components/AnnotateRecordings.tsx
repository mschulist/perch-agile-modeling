"use client"
import React, { useEffect, useRef, useState } from "react"
import Image from "next/image"
import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import AnnotationButtons from "./AnnotationButtons"
import { useAuth, useProject } from "./Auth"
import { set } from "firebase/database"
import AnnotationDirections from "./AnnotationDirections"

const voc_types = ["call", "song"]

export default function AnnotateRecordings() {
    const [example, setExample] = useState<precomputedExample | null>(null)

    const user = useAuth()
    const project = useProject()

    useEffect(() => {
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
            <div className="flex flex-col justify-start w-1/4 p-4">
                <AnnotationDirections />
            </div>
            <div className="flex flex-col w-1/2">
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
                        />
                    </>
                )}
            </div>
        </div>
    )
}

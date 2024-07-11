"use client"
import React, { useEffect, useRef, useState } from "react"
import Image from "next/image"
import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import AnnotationButtons from "./AnnotationButtons"
import { useAuth, useProject } from "./Auth"
import { set } from "firebase/database"

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
        <div className="flex flex-col justify-center items-center">
            <Button variant="outline" className="m-2" onClick={getNextExample}>
                Skip Recording
            </Button>
            {example && (
                <>
                    <Image
                        src={example.spec_url}
                        alt=""
                        width={500}
                        height={500}
                        className="m-4 rounded-xl"
                    />
                    <audio controls src={example.audio_url} className="m-4" />
                    <AnnotationButtons
                        example={example}
                        getNextExample={getNextExample}
                    />
                </>
            )}
        </div>
    )
}

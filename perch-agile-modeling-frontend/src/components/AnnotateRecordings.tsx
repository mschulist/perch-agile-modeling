"use client"
import React, { useEffect, useRef, useState } from "react"
import Image from "next/image"
import { precomputedExample } from "@/models/precomputedExample"
import { set } from "firebase/database"

export default function AnnotateRecordings() {
    const [example, setExample] = useState<precomputedExample | null>(null)

    useEffect(() => {
        fetch("api/getNextExample", {
            method: "POST",
            body: JSON.stringify({
                project: "caples-testing",
                exampleType: "targetRecordings",
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            setExample(data.example)
        })
    }, [])
    return (
        <div className="flex flex-col justify-center items-center">
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
                </>
            )}
        </div>
    )
}

"use client"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useState } from "react"
import { CheckSourceInfoResponse } from "@/models/sourceInfos"
import { SourceInfoEmbedButton } from "./SourceInfoEmbedButton"
import { Button } from "@/components/ui/button"

export default function SourceInfos() {
    const [sourceInfos, setSourceInfos] = useState<string>("gs://")
    const [files, setFiles] = useState<string[]>([])
    const [validSourceInfos, setValidSourceInfos] = useState<boolean | null>(
        null
    )
    const [sourceInfoError, setSourceInfoError] = useState<string | undefined>(
        ""
    )
    const [project, setProject] = useState<string>("caples-testing")
    // TODO: add ability to set project here based on auth

    const checkSourceInfos = async () => {
        fetch("api/checkSourceGlobs", {
            method: "POST",
            body: JSON.stringify({ glob: sourceInfos }),
        }).then(async (res) => {
            const data: CheckSourceInfoResponse = await res.json()
            setFiles(data.files)
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                setSourceInfoError(data.error)
                return
            }
            if (data.files.length > 0) {
                setValidSourceInfos(true)
                setSourceInfoError(undefined)
            } else {
                setValidSourceInfos(false)
            }
        })
    }

    const startEmbedding = () => {
        console.log("Embedding source infos")
    }

    return (
        <div className="flex flex-col px-32 items-center">
            <Label htmlFor="sourceInfoInput" className="my-4">
                Source Info glob:
            </Label>
            <Input
                id="sourceInfoInput"
                placeholder="Enter Source Info glob here"
                className="w-1/3 min-w-[375px]"
                value={sourceInfos}
                onChange={(e) => {
                    setSourceInfos(e.target.value)
                }}
            />
            <Button
                onClick={checkSourceInfos}
                variant="outline"
                className="my-4"
            >
                Check Source Infos
            </Button>
            {files.length > 0 && (
                <div className="flex flex-col items-center">
                    <h1 className="text-2xl font-bold">First 100 files:</h1>
                    <div className="w-full min-w-[500px] h-96 overflow-y-scroll bg-gray-800 mt-4 p-4 rounded-xl">
                        {files.slice(0, 100).map((file, index) => (
                            <div key={index} className="py-1">
                                {file}
                            </div>
                        ))}
                    </div>
                </div>
            )}
            {!validSourceInfos && validSourceInfos !== null && (
                <p className="text-red-500">
                    No files found for the given glob
                </p>
            )}
            {sourceInfoError && (
                <p className="text-red-500">{sourceInfoError}</p>
            )}
            {validSourceInfos && (
                <div className="p-4">
                    <SourceInfoEmbedButton onClick={startEmbedding} />
                </div>
            )}
        </div>
    )
}

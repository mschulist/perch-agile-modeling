"use client"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { set } from "firebase/database"
import { useState } from "react"
import { CheckSourceInfoResponse } from "@/models/sourceInfos"

export default function SourceInfos() {
    const [sourceInfos, setSourceInfos] = useState<string>("gs://")
    const [files, setFiles] = useState<string[]>([])

    const checkSourceInfos = async () => {
        fetch("api/checkSourceGlobs", {
            method: "POST",
            body: JSON.stringify({ glob: sourceInfos }),
        }).then(async (res) => {
            const data: CheckSourceInfoResponse = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            setFiles(data.files)
        })
    }

    return (
        <div className="flex flex-col px-32 items-center">
            <Label htmlFor="sourceInfoInput" className="my-4">
                Source Info globs:
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
            <button
                onClick={checkSourceInfos}
                className="my-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
                Check Source Infos
            </button>
            {files.length > 0 && (
                <div className="flex flex-col items-center">
                    <h1 className="text-2xl font-bold">First 100 files:</h1>
                    <div className="w-full min-w-[500px] h-96 overflow-y-scroll bg-gray-800 mt-4 p-4">
                        {files.slice(0, 100).map((file, index) => (
                            <div key={index} className="py-1">
                                {file}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

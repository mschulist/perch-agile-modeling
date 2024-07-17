import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import { useAuth, useProject } from "./Auth"
import { useState } from "react"
import { Input } from "./ui/input"
import AutoSuggestLabel from "./AutoSuggestLabel"

export default function AnnotationButtons({
    example,
    getNextExample,
    exampleClasses,
}: {
    example: precomputedExample
    getNextExample: () => void
    exampleClasses: string[]
}) {
    const voc_types = ["call", "song"]
    const [customSpecies, setCustomSpecies] = useState<string>("")

    const user = useAuth()
    const project = useProject()

    function annotateRecording(voc_type: string) {
        fetch("api/annotateRecording", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                example: example,
                voc_type: voc_type,
                user: user,
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
        })
    }

    return (
        <div className="flex flex-col self-center">
            <p className="self-center">If {example.species} is present:</p>
            {voc_types.map((voc_type) => (
                <Button
                    variant="outline"
                    key={`${example.species}_${voc_type}`}
                    className="m-2 self-center"
                    value={voc_type}
                    onClick={() => {
                        annotateRecording(voc_type)
                        getNextExample()
                    }}
                >
                    {`${example.species}_${voc_type}`}
                </Button>
            ))}
            <p className="self-center p-2">
                If {example.species} is not present, but another species is:
            </p>
            <div className="self-center">
                <AutoSuggestLabel
                    suggestions={exampleClasses}
                    setCustomSpecies={setCustomSpecies}
                    customSpecies={customSpecies}
                />
            </div>
            <Button
                variant="outline"
                className="m-2 self-center"
                value={customSpecies}
                onClick={() => {
                    annotateRecording(customSpecies)
                    getNextExample()
                }}
                style={{ display: customSpecies === "" ? "none" : "block" }}
            >
                Annotate as: {customSpecies}
            </Button>

            <p className="self-center p-2">If there are no birds present:</p>
            <Button
                variant="outline"
                className="m-2 self-center"
                value="unknown"
                onClick={() => {
                    annotateRecording("unknown")
                    getNextExample()
                }}
            >
                no birds present
            </Button>

            <p className="self-center p-2">If you would like to review later:</p>
            <Button
                variant="outline"
                className="m-2 self-center"
                value="review"
                onClick={() => {
                    annotateRecording("review")
                    getNextExample()
                }}
            >
                review later
            </Button>
        </div>
    )
}

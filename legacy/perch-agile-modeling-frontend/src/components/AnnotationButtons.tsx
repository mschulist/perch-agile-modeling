import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import { useAuth, useProject } from "./Auth"
import { useState } from "react"
import AutoSuggestLabel from "./AutoSuggestLabel"

export default function AnnotationButtons({
    example,
    getNextExample,
    exampleClasses,
    finishAnnotation,
}: {
    example: precomputedExample
    getNextExample: () => void
    exampleClasses: string[]
    finishAnnotation: () => Promise<void>
}) {
    const voc_types = ["call", "song"]
    const [customSpecies, setCustomSpecies] = useState<string>("")

    const user = useAuth()
    const project = useProject()

    async function annotateRecording(label: string) {
        fetch("api/annotateRecording", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                example: example,
                label: label,
                user: user,
            }),
        }).then(async (res) => {
            const data = await res.json()
            console.log("annotation response", data)
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
                        finishAnnotation().then(() => {
                            annotateRecording(
                                `${example.species}_${voc_type}`
                            ).then(() => {
                                getNextExample()
                            })
                        })
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
                    finishAnnotation().then(() => {
                        console.log("finishing annotation")
                        annotateRecording(customSpecies).then(() => {
                            console.log("getting next example")
                            getNextExample()
                        })
                    })
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
                    finishAnnotation().then(() => {
                        annotateRecording("unknown").then(() => {
                            getNextExample()
                        })
                    })
                }}
            >
                no birds present
            </Button>

            <p className="self-center p-2">
                If you would like to review later:
            </p>
            <Button
                variant="outline"
                className="m-2 self-center"
                value="review"
                onClick={() => {
                    finishAnnotation().then(() => {
                        annotateRecording("review").then(() => {
                            getNextExample()
                        })
                    })
                }}
            >
                review later
            </Button>
        </div>
    )
}

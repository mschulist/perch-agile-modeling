import { precomputedExample } from "@/models/precomputedExample"
import { Button } from "./ui/button"
import { useAuth, useProject } from "./Auth"

export default function AnnotationButtons({
    example,
    getNextExample,
}: {
    example: precomputedExample
    getNextExample: () => void
}) {
    const voc_types = ["call", "song"]

    const user = useAuth()
    const project = useProject()

    function annotateRecording(voc_type: string) {
        fetch("api/annotateRecording", {
            method: "POST",
            body: JSON.stringify({
                project: project,
                example: example,
                voc_type: voc_type,
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
        <div className="flex flex-col">
            {voc_types.map((voc_type) => (
                <Button
                    variant="outline"
                    key={`${example.species}_${voc_type}`}
                    className="m-2"
                    value={voc_type}
                    onClick={() => {
                        annotateRecording(voc_type)
                        getNextExample()
                    }}
                >
                    {`${example.species}_${voc_type}`}
                </Button>
            ))}
            <Button
                variant="outline"
                className="m-2"
                value="unknown"
                onClick={() => {
                    annotateRecording("unknown")
                    getNextExample()
                }}
            >
                unknown
            </Button>
        </div>
    )
}

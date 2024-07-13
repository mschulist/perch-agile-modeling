import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { existingLabeledOutput } from "@/models/existingExamples"
import { Button } from "./ui/button"
import Image from "next/image"
import { Input } from "./ui/input"
import { useState } from "react"
import { useProject } from "./Auth"
import AutoSuggestLabel from "./AutoSuggestLabel"

export default function MoveLabeledExampleDialog({
    example,
    exampleClasses,
    getExamples,
    getLabeledExamples,
}: {
    example: existingLabeledOutput
    exampleClasses: string[]
    getExamples: () => void
    getLabeledExamples: (exampleClass: string) => void
}) {
    const [customSpecies, setCustomSpecies] = useState<string>("")

    const project = useProject()

    function moveExample() {
        fetch("api/moveLabeledOutput", {
            method: "POST",
            body: JSON.stringify({
                example: example,
                newExampleClass: customSpecies,
                project: project,
            }),
        }).then(async (res) => {
            const data = await res.json()
            if (!data.success) {
                console.error("Error occurred during fetch:", data.error)
                return
            }
            console.log("Successfully moved example")
            setCustomSpecies("")
            getExamples()
            getLabeledExamples(example.exampleClass)
        })
    }

    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button
                    variant="outline"
                    className="bg-green-700 hover:bg-green-800 mb-2"
                >
                    Move Example
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>
                        Current Label:{" "}
                        <span className="text-orange-300">
                            {example.exampleClass}
                        </span>
                        <br />
                        <div className="flex flex-row items-center mt-4">
                            Move to:
                            <div className="ml-2">
                                <AutoSuggestLabel
                                    suggestions={exampleClasses}
                                    setCustomSpecies={setCustomSpecies}
                                    customSpecies={customSpecies}
                                />
                            </div>
                        </div>
                    </DialogTitle>
                    <DialogDescription>
                        {example.spec_url && (
                            <Image
                                src={example.spec_url}
                                alt=""
                                height={600}
                                width={600}
                                className="rounded-xl"
                            />
                        )}
                        <br />
                        Filename: {example.filename}
                        <br />
                        Timestamp: {example.timestampS} seconds
                        <br />
                        <audio
                            src={example.audio_url}
                            controls
                            className="pb-4"
                        />
                    </DialogDescription>
                </DialogHeader>

                <DialogFooter>
                    <DialogClose asChild>
                        <Button
                            onClick={() => moveExample()}
                            disabled={
                                customSpecies === "" ||
                                customSpecies === example.exampleClass
                            }
                            className=""
                        >
                            Move to: {customSpecies}
                        </Button>
                    </DialogClose>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

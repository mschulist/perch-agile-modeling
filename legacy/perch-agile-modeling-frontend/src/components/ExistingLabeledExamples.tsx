import { existingLabeledOutput } from "@/models/existingExamples"
import Image from "next/image"
import MoveLabeledExampleDialog from "./MoveLabeledExampleDialog"

export default function ExistingLabeledExamples({
    labeledExamples,
    exampleClasses,
    getLabeledExamples,
    getExamples,
}: {
    labeledExamples: existingLabeledOutput[]
    exampleClasses: string[]
    getLabeledExamples: (exampleClass: string) => void
    getExamples: () => void
}) {
    return (
        <div className="flex flex-col m-10 w-full">
            <ul className="list-disc px-5 h-[42rem] overflow-y-scroll">
                {labeledExamples.map((example) => (
                    <li key={`${example.filename}.${example.audio_url}`}>
                        Filename: {example.filename}
                        <br />
                        Timestamp: {example.timestampS} seconds
                        {example.spec_url && (
                            <Image
                                src={example.spec_url}
                                alt=""
                                height={480}
                                width={640}
                                unoptimized
                                className="rounded-xl h-full w-[640px]"
                            />
                        )}
                        <MoveLabeledExampleDialog
                            example={example}
                            exampleClasses={exampleClasses}
                            getLabeledExamples={getLabeledExamples}
                            getExamples={getExamples}
                        />
                        <audio
                            src={example.audio_url}
                            controls
                            className="pb-4"
                            preload="none"
                        />
                    </li>
                ))}
            </ul>
        </div>
    )
}

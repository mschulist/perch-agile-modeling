import { Storage } from "@google-cloud/storage"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"
import { precomputedExample } from "@/models/precomputedExample"
import { NextResponse } from "next/server"

const storage = new Storage({
    keyFilename: "./src/app/api/caples-storage-key.json",
})

export async function POST(request: Request) {
    const alreadyLabeledFile = await findAlreadyLabeledFile()
    const alreadyLabeled = await getAlreadyLabeledExamples(alreadyLabeledFile)
    const example = await getNextExample(
        "gs://bird-ml/caples-data/precomputed_raven/",
        alreadyLabeled
    )
    if (example === null) {
        return new Response(
            JSON.stringify({
                success: false,
                error: "No more examples to label, you're done!",
            })
        )
    }
    console.log(example)
    return NextResponse.json({ success: true, example })
}

async function getNextExample(
    searchResultsDir: string,
    alreadyLabeled: Set<string>
): Promise<precomputedExample | null> {
    const { bucket, path } = splitPathIntoBucketAndPath(searchResultsDir)

    const precomputedExamples = await storage
        .bucket(bucket)
        .getFiles({ matchGlob: `${path}*.wav` })

    const examples = precomputedExamples[0].map((file) => {
        return pathlib.basename(file.name)
    })

    for (const example of examples) {
        if (!alreadyLabeled.has(example)) {
            const [filename, timestampS, species] = example.split("^_^")
            const audio_url = `https://storage.googleapis.com/${bucket}/${path}${example}`
            const spec_url = `https://storage.googleapis.com/${bucket}/${path}${example.slice(
                0,
                -4
            )}.png`
            const precomputedExample: precomputedExample = {
                audio_url,
                spec_url,
                filename,
                species,
                timestampS: Number(timestampS),
            }
            return precomputedExample
        }
    }
    return null
}

async function getAlreadyLabeledExamples(
    alreadyLabeledFile: string
): Promise<Set<string>> {
    const { bucket, path } = splitPathIntoBucketAndPath(alreadyLabeledFile)
    console.log(bucket, path)
    const alreadyLabeled = (
        await storage.bucket(bucket).file(path).download()
    ).toString()
    const alreadyLabeledLines = new Set(alreadyLabeled.split("\n"))
    return alreadyLabeledLines
}

async function findAlreadyLabeledFile() {
    // TODO: we want to store this file location in firebase and retrieve it here
    return "gs://bird-ml/caples-data/labeled_outputs/finished_raven.csv"
}

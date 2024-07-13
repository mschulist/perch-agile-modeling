import { Storage } from "@google-cloud/storage"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"
import { precomputedExample } from "@/models/precomputedExample"
import { NextResponse } from "next/server"

const GS_SERVICE_ACCOUNT = JSON.parse(process.env.GS_SERVICE_ACCOUNT as string)

const storage = new Storage({
    credentials: GS_SERVICE_ACCOUNT,
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
    await addToAlreadyLabeledFile(alreadyLabeledFile, example)
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
            let [filename, timestampS, species] = example.split("^_^")
            species = species.slice(0, -4)
            const audio_url = `https://storage.googleapis.com/${bucket}/${path}${example}`
            const spec_url = `https://storage.googleapis.com/${bucket}/${path}${example.slice(
                0,
                -4
            )}.png`
            const gsuri = `gs://${bucket}/${path}${example}`
            const precomputedExample: precomputedExample = {
                gsuri,
                audio_url,
                spec_url,
                filename,
                species,
                timestampS: timestampS,
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

async function addToAlreadyLabeledFile(
    alreadyLabeledFile: string,
    example: precomputedExample
) {
    const { bucket, path } = splitPathIntoBucketAndPath(alreadyLabeledFile)
    let file = (await storage.bucket(bucket).file(path).download()).toString()
    const currDatetime = new Date().toISOString()
    // file += `${currDatetime}\n${example.filename}^_^${example.timestampS}^_^${example.species}.wav\n`
    await storage.bucket(bucket).file(path).save(file)
}

async function findAlreadyLabeledFile() {
    // TODO: we want to store this file location in firebase and retrieve it here
    return "gs://bird-ml/caples-data/labeled_outputs/finished_raven.csv"
}

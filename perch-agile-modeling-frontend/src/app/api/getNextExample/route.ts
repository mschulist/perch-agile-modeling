import {
    getGoogleStorage,
    splitPathIntoBucketAndPath,
} from "@/utils/gcloud_utils"
import pathlib from "path"
import { precomputedExample } from "@/models/precomputedExample"
import { NextResponse } from "next/server"
import {
    getAdminFirestoreDB,
    findAlreadyLabeledFile,
    getExamplesPath,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

const storage = getGoogleStorage()

export async function POST(request: Request) {
    const response = await request.json()
    const project: string = response.project
    const alreadyLabeledFile = await findAlreadyLabeledFile(project, db)
    const alreadyLabeled = await getAlreadyLabeledExamples(alreadyLabeledFile)
    const examplesPath = await getExamplesPath(project, "searchResults", db)
    const example = await getNextExample(examplesPath, alreadyLabeled)
    if (example === null) {
        return NextResponse.json({
            success: false,
            error: "No more examples to label, you're done!",
        })
    }
    return NextResponse.json({ success: true, example })
}

async function getNextExample(
    searchResultsDir: string,
    alreadyLabeled: Set<string>
): Promise<precomputedExample | null> {
    const { bucket, path } = splitPathIntoBucketAndPath(searchResultsDir)

    const precomputedExamples = await storage
        .bucket(bucket)
        .getFiles({ matchGlob: `${path}/*` })

    let examples: { [key: string]: { spec?: any; audio?: any } } = {}
    precomputedExamples[0].forEach((example) => {
        const basename = pathlib.basename(example.name).slice(0, -4)
        if (example.name.endsWith(".png")) {
            if (basename in examples) {
                examples[basename].spec = example
            } else {
                examples[basename] = {
                    spec: example,
                }
            }
        } else if (example.name.endsWith(".wav")) {
            if (basename in examples) {
                examples[basename].audio = example
            } else {
                examples[basename] = {
                    audio: example,
                }
            }
        }
    })

    for (const example of Object.values(examples)) {
        const basename = pathlib.basename(example.spec.name).slice(0, -4)
        // check to see if the example has an audio file AND a spectrogram file
        if (
            !alreadyLabeled.has(`${basename}.wav`) &&
            example.audio &&
            example.spec
        ) {
            let [filename, timestampS, species] = basename.split("^_^")
            const audio_url = (
                await example.audio.getSignedUrl({
                    action: "read",
                    expires: Date.now() + 15 * 60 * 1000,
                })
            )[0]
            const spec_url = (
                await example.spec.getSignedUrl({
                    action: "read",
                    expires: Date.now() + 15 * 60 * 1000,
                })
            )[0]

            const gsuri = `gs://${bucket}/${path}/${basename}.wav`
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
    const alreadyLabeled = (
        await storage.bucket(bucket).file(path).download()
    ).toString()
    const alreadyLabeledLines = new Set(alreadyLabeled.split("\n"))
    return alreadyLabeledLines
}


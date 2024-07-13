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
    console.log("examplesPath", examplesPath)
    const example = await getNextExample(examplesPath, alreadyLabeled)
    if (example === null) {
        return NextResponse.json({
            success: false,
            error: "No more examples to label, you're done!",
        })
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
        if (!alreadyLabeled.has(basename)) {
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

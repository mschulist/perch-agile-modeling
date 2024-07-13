import { NextResponse } from "next/server"
import { ExampleType, existingLabeledOutput } from "@/models/existingExamples"
import {
    getGoogleStorage,
    splitPathIntoBucketAndPath,
} from "@/utils/gcloud_utils"
import pathlib from "path"
import {
    getAdminFirestoreDB,
    getExamplesPath,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()
const storage = getGoogleStorage()

/**
 * Handles the POST request.
 * @param request - The request object.
 * @returns A JSON response with the success status and examples.
 */
export async function POST(request: Request): Promise<NextResponse> {
    const body = await request.json()
    const project = body.project
    const exampleClass = body.exampleClass
    const exampleType: ExampleType = body.exampleType
    const examplesPath = await getExamplesPath(project, exampleType, db)
    const precomputed_dir = await getExamplesPath(project, "searchResults", db)
    const examples = await getExamplesSingleFolder(
        examplesPath,
        exampleClass,
        precomputed_dir
    )
    return NextResponse.json({ success: true, examples })
}

/**
 * Retrieves a list of existing labeled outputs for a given examples folder and class.
 *
 * @param examplesPath - The path to the examples folder.
 * @param exampleClass - The class of the examples.
 * @returns A promise that resolves to an array of existing labeled outputs.
 */
async function getExamplesSingleFolder(
    examplesPath: string,
    exampleClass: string,
    precomputed_dir: string
): Promise<existingLabeledOutput[]> {
    const { bucket, path } = splitPathIntoBucketAndPath(examplesPath)
    const exampleClassPath = pathlib.join(path, exampleClass)
    const files = (
        await storage.bucket(bucket).getFiles({ prefix: exampleClassPath })
    )[0]
    const examplesPromises = files.map(async (file) => {
        const name = file.name
        const basename = pathlib.basename(name)
        let [filename, timestampS] = basename.split("__")
        timestampS = timestampS.split(".")[0] // remove file extension
        const gsuri = `gs://${bucket}/${path}/${exampleClass}/${basename}`
        const audio_url = (
            await file.getSignedUrl({
                expires: Date.now() + 1000 * 60 * 60 * 24 * 1,
                action: "read",
            })
        )[0]
        const spec_url = await getPrecomputedSpecUrl(
            precomputed_dir,
            filename,
            timestampS
        )
        if (!spec_url) {
            return { exampleClass, filename, timestampS, gsuri, audio_url }
        }

        return {
            exampleClass,
            filename,
            timestampS,
            gsuri,
            audio_url,
            spec_url,
        }
    })
    const examples = await Promise.all(examplesPromises)
    return examples
}

async function getPrecomputedSpecUrl(
    precomputed_dir: string,
    filename: string,
    timestampS: string
): Promise<string | null> {
    const { bucket, path } = splitPathIntoBucketAndPath(precomputed_dir)
    const fileglob = pathlib.join(path, `*${filename}*^_^${timestampS}.0^_^*.png`)
    console.log("fileglob", fileglob)
    const files = (
        await storage.bucket(bucket).getFiles({ matchGlob: fileglob })
    )[0]
    if (files.length === 0) {
        return null
    }

    const spec_url = (
        await files[0].getSignedUrl({
            expires: Date.now() + 1000 * 60 * 60 * 24 * 1,
            action: "read",
        })
    )[0]
    return spec_url
}

import { Storage } from "@google-cloud/storage"
import { NextResponse } from "next/server"
import firebaseAdmin from "firebase-admin"
import { cert, ServiceAccount } from "firebase-admin/app"
import { getFirestore } from "firebase-admin/firestore"
import {
    ExampleType,
    Example,
    existingLabeledOutput,
} from "@/models/existingExamples"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"

const FIREBASE_SERVICE_ACCOUNT = JSON.parse(
    process.env.FIREBASE_SERVICE_ACCOUNT as string
)

/**
 * Initializes the Firebase app with the provided service account credentials.
 */
!firebaseAdmin.apps.length
    ? firebaseAdmin.initializeApp({
          credential: cert(FIREBASE_SERVICE_ACCOUNT as string | ServiceAccount),
      })
    : firebaseAdmin.app()

const db = getFirestore()

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
    const examplesPath = await getExamplesPath(project, exampleType)
    const precomputed_dir = await getExamplesPath(project, "searchResults")
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
    const storage = new Storage()
    const { bucket, path } = splitPathIntoBucketAndPath(examplesPath)
    const exampleClassPath = pathlib.join(path, exampleClass)
    const files = (
        await storage.bucket(bucket).getFiles({ prefix: exampleClassPath })
    )[0]
    const examples: existingLabeledOutput[] = files.map((file) => {
        const name = file.name
        const basename = pathlib.basename(name)
        let [filename, timestampS] = basename.split("__")
        timestampS = timestampS.split(".")[0] // remove file extension
        file.getSignedUrl
        const gsuri = `gs://${bucket}/${path}/${exampleClass}/${basename}`
        const audio_url = `https://storage.googleapis.com/${bucket}/${path}/${exampleClass}/${basename}`
        return { exampleClass, filename, timestampS, gsuri, audio_url }
    })
    return examples
}

async function getPrecomputedSpecUrl(
    precomputed_dir: string,
    filename: string,
    timestampS: string
): Promise<string> {
    const storage = new Storage()
    const { bucket, path } = splitPathIntoBucketAndPath(precomputed_dir)
    const fileglob = pathlib.join(path, `*${filename}*${timestampS}*.png`)
    const file = (
        await storage.bucket(bucket).getFiles({ matchGlob: fileglob })
    )[0][0]
    console.log(file)
    return file.publicUrl()
}

/**
 * Retrieves the examples path for a given project and example type.
 * @param project - The project name.
 * @param exampleType - The type of example.
 * @returns The examples path.
 * @throws Error if project info or examples path is not found.
 */
async function getExamplesPath(
    project: string,
    exampleType: ExampleType
): Promise<string> {
    const projectInfo = (
        await db.collection("projects").doc(project).get()
    ).data()

    console.log(projectInfo)

    if (!projectInfo) {
        throw new Error("Project info not found")
    }

    const examplesPath = projectInfo[exampleType]

    if (!examplesPath) {
        throw new Error("No examples path found for project")
    }

    return examplesPath
}

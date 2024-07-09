import { Storage } from "@google-cloud/storage"
import { NextResponse } from "next/server"
import firebaseAdmin from "firebase-admin"
import { initializeApp, cert, ServiceAccount } from "firebase-admin/app"
import { getFirestore } from "firebase-admin/firestore"
import { ExampleType, Example } from "@/models/existingExamples"
import serviceAccount from "../caples-firebase-adminsdk-hp0f6-fcca47250d.json"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"

/**
 * Initializes the Firebase app with the provided service account credentials.
 */
!firebaseAdmin.apps.length
    ? firebaseAdmin.initializeApp({
          credential: cert(serviceAccount as string | ServiceAccount),
      })
    : firebaseAdmin.app()

/**
 * Handles the GET request.
 * @param request - The request object.
 */
export async function POST(request: Request) {
    const body = await request.json()
    const project = body.project
    const exampleType: ExampleType = body.exampleType
    const examplesPath = await getExamplesPath(project, exampleType)
    const examples = await getExamplesBasedOnType(examplesPath, exampleType)
    return NextResponse.json({ success: true, examples })
}

async function getExamplesBasedOnType(
    examplesPath: string,
    exampleType: ExampleType
) {
    switch (exampleType) {
        case "targetRecordings":
            return getExistingExamplesFolders(examplesPath)
        case "labeledOutputs":
            return getExistingExamplesFolders(examplesPath)
        case "searchResults":
            return getExistingExamplesSingleFolder(examplesPath)
        default:
            throw new Error("Invalid example type")
    }
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
    const db = getFirestore()
    // TODO: make this actually work lol
    // console.log(await db.collection("projects").listDocuments())
    // const projectInfo = (
    //     await db.collection("projects").doc(project).get()
    // ).data()

    // // console.log(projectInfo)

    // if (!projectInfo) {
    //     throw new Error("Project info not found")
    // }

    // const examplesPath = projectInfo.data()[exampleType]

    // if (!examplesPath) {
    //     throw new Error("No examples path found for project")
    // }

    return "gs://bird-ml/caples-data/target_recordings"
}

/**
 * Retrieves the existing examples folders for a given project.
 * Only use for examples that are in the "folders of folders" format.
 * @param examplesPath - The examples path.
 * @returns The existing examples folders.
 */
async function getExistingExamplesFolders(
    examplesPath: string
): Promise<Example[]> {
    const storage = new Storage()

    const examples: Example[] = []

    let examplesDict: { [key: string]: any } = {}

    const { bucket, path } = splitPathIntoBucketAndPath(examplesPath)
    const files = (
        await storage.bucket(bucket).getFiles({ matchGlob: `${path}/*/*` })
    )[0]

    const fileNames = files.map((file) => file.name)

    for (const fileName of fileNames) {
        const folder = pathlib.basename(pathlib.dirname(fileName))
        if (folder in examplesDict) {
            examplesDict[folder]++
        } else {
            examplesDict[folder] = 1
        }
    }

    for (const folder in examplesDict) {
        examples.push({
            class: folder,
            number: examplesDict[folder],
        })
    }

    return examples
}

async function getExistingExamplesSingleFolder(
    examplesPath: string
): Promise<Example[]> {
    throw new Error("Not implemented yet")
}

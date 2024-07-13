import { Storage } from "@google-cloud/storage"
import { NextResponse } from "next/server"
import { ExampleType, Example } from "@/models/existingExamples"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"
import {
    getExamplesPath,
    getAdminFirestoreDB,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

/**
 * Handles the POST request.
 * @param request - The request object.
 * @returns A JSON response with the success status and examples.
 */
export async function POST(request: Request): Promise<NextResponse> {
    const body = await request.json()
    const project = body.project
    const exampleType: ExampleType = body.exampleType
    const examplesPath = await getExamplesPath(project, exampleType, db)
    const examples = await getExamplesBasedOnType(examplesPath, exampleType)
    return NextResponse.json({ success: true, examples })
}

/**
 * Retrieves the examples based on the example type.
 * @param examplesPath - The path to the examples.
 * @param exampleType - The type of example.
 * @returns A promise that resolves to an array of examples.
 * @throws Error if the example type is invalid.
 */
async function getExamplesBasedOnType(
    examplesPath: string,
    exampleType: ExampleType
): Promise<Example[]> {
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

    let examplesDict: { [key: string]: number } = {}

    const { bucket, path } = splitPathIntoBucketAndPath(examplesPath)
    const files = (
        await storage.bucket(bucket).getFiles({ matchGlob: `${path}/*/*.wav` })
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

/**
 * Retrieves the existing examples for a given project.
 * Only use for examples that are in a single folder.
 * @param examplesPath - The examples path.
 * @returns The existing examples.
 * @throws Error if the function is not implemented yet.
 */
async function getExistingExamplesSingleFolder(
    examplesPath: string
): Promise<Example[]> {
    const storage = new Storage()

    let examplesDict: { [key: string]: number } = {}

    const { bucket, path } = splitPathIntoBucketAndPath(examplesPath)

    const files = (
        await storage.bucket(bucket).getFiles({ matchGlob: `${path}/*.wav` })
    )[0]

    const fileNames = files.map((file) => file.name)

    for (const fileName of fileNames) {
        let [file, timestampS, species] = pathlib
            .basename(fileName)
            .split("^_^")
        species = species.split(".")[0] // get rid of the file extension
        if (species in examplesDict) {
            examplesDict[species]++
        } else {
            examplesDict[species] = 1
        }
    }

    const examples: Example[] = []

    for (const species in examplesDict) {
        examples.push({
            class: species,
            number: examplesDict[species],
        })
    }
    return examples
}

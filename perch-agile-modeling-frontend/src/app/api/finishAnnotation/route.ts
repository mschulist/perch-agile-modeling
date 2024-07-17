import {
    getGoogleStorage,
    splitPathIntoBucketAndPath,
} from "@/utils/gcloud_utils"
import { NextResponse } from "next/server"
import { moveFile } from "@/utils/gcloud_utils"
import {
    findAlreadyLabeledFile,
    getAdminFirestoreDB,
} from "@/utils/firebaseServerUtils"
import { Example } from "@/models/existingExamples"
import { precomputedExample } from "@/models/precomputedExample"

const db = getAdminFirestoreDB()

const storage = getGoogleStorage()

export async function POST(request: Request): Promise<NextResponse> {
    const response = await request.json()
    const project: string = response.project
    const example: precomputedExample = response.example
    const alreadyLabeledFile = await findAlreadyLabeledFile(project, db)
    await addToAlreadyLabeledFile(alreadyLabeledFile, example)
    return NextResponse.json({ success: true })
}

async function addToAlreadyLabeledFile(
    alreadyLabeledFile: string,
    example: precomputedExample
) {
    const { bucket, path } = splitPathIntoBucketAndPath(alreadyLabeledFile)
    let file = (await storage.bucket(bucket).file(path).download()).toString()
    const currDatetime = new Date().toISOString()
    file += `${currDatetime}\n${example.filename}^_^${example.timestampS}^_^${example.species}.wav\n`
    await storage.bucket(bucket).file(path).save(file)
    console.log(`Successfully added ${file} to ${alreadyLabeledFile}`)
}

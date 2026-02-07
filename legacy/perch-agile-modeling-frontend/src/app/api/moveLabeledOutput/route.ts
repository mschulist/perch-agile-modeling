import { getGoogleStorage } from "@/utils/gcloud_utils"
import pathlib from "path"
import { NextResponse } from "next/server"
import { moveFile } from "@/utils/gcloud_utils"
import { existingLabeledOutput } from "@/models/existingExamples"
import {
    getAdminFirestoreDB,
    getLabeledOutputLocation,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

const storage = getGoogleStorage()

export async function POST(request: Request): Promise<NextResponse> {
    let response = await request.json()
    const project = response.project
    const example: existingLabeledOutput = response.example
    const newExampleClass = response.newExampleClass
    const basename = pathlib.basename(example.gsuri)

    const labeledOutputLocation = await getLabeledOutputLocation(project, db)
    const newGsuri = `${labeledOutputLocation}/${newExampleClass}/${basename}`
    console.log(`Moving ${example.gsuri} to ${newGsuri}`)
    moveFile(example.gsuri, newGsuri, storage, true)
    return NextResponse.json({ success: true })
}

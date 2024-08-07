import {
    getGoogleStorage,
    splitPathIntoBucketAndPath,
} from "@/utils/gcloud_utils"
import { NextResponse } from "next/server"
import { moveFile } from "@/utils/gcloud_utils"
import {
    getAdminFirestoreDB,
    getLabeledOutputLocation,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

const storage = getGoogleStorage()

export async function POST(request: Request): Promise<NextResponse> {
    const { project, example, label } = await request.json()

    const { bucket, path } = splitPathIntoBucketAndPath(example.gsuri)
    const filename = example.filename.slice(0, -4) // remove .wav extension
    const timestampS = example.timestampS
    const newFilename = `${filename}___${timestampS}.wav`

    const labeledOutputLocation = await getLabeledOutputLocation(project, db)
    const newGsuri = `${labeledOutputLocation}/${label}/${newFilename}`
    moveFile(example.gsuri, newGsuri, storage)
    return NextResponse.json({ success: true })
}

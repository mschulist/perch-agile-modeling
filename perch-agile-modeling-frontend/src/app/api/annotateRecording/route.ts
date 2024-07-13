import {
    getGoogleStorage,
    splitPathIntoBucketAndPath,
} from "@/utils/gcloud_utils"
import { NextResponse } from "next/server"
import { moveFile } from "@/utils/gcloud_utils"
import firebaseAdmin from "firebase-admin"
import {
    getAdminFirestoreDB,
    getLabeledOutputLocation,
} from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

const storage = getGoogleStorage()

export async function POST(request: Request): Promise<NextResponse> {
    const { project, example, voc_type } = await request.json()

    const { bucket, path } = splitPathIntoBucketAndPath(example.gsuri)
    const filename = example.filename.slice(0, -4) // remove .wav extension
    const timestampS = example.timestampS
    const newFilename = `${filename}___${timestampS}.wav`
    let newSpecies = `${example.species}_${voc_type}`
    if (voc_type === "unknown") {
        newSpecies = "unknown"
    }

    const labeledOutputLocation = await getLabeledOutputLocation(project, db)
    const newGsuri = `${labeledOutputLocation}/${newSpecies}/${newFilename}`
    moveFile(example.gsuri, newGsuri, storage)
    return NextResponse.json({ success: true })
}

import { Storage } from "@google-cloud/storage"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"
import pathlib from "path"
import { precomputedExample } from "@/models/precomputedExample"
import { NextResponse } from "next/server"

const GS_SERVICE_ACCOUNT = JSON.parse(process.env.GS_SERVICE_ACCOUNT as string)

const storage = new Storage({
    credentials: GS_SERVICE_ACCOUNT,
})

export async function POST(request: Request): Promise<NextResponse> {
    const { project, example, voc_type } = await request.json()

    const { bucket, path } = splitPathIntoBucketAndPath(example.gsuri)
    const filename = example.filename.slice(0, -4) // remove .wav extension
    const timestampS = example.timestampS
    const newFilename = `${filename}__${timestampS}.wav`
    let newSpecies = `${example.species}_${voc_type}`
    if (voc_type === "unknown") {
        newSpecies = "unknown"
    }

    const labeledOutputLocation = await getLabeledOutputLocation(project)
    const newGsuri = `${labeledOutputLocation}${newSpecies}/${newFilename}`
    moveFile(example.gsuri, newGsuri)
    return NextResponse.json({ success: true })
}

async function moveFile(oldGsuri: string, newGsuri: string) {
    const { bucket: oldBucket, path: oldPath } =
        splitPathIntoBucketAndPath(oldGsuri)
    const { bucket: newBucket, path: newPath } =
        splitPathIntoBucketAndPath(newGsuri)

    const file = storage.bucket(oldBucket).file(oldPath)
    await file.copy(newPath)
    console.log(`Copied ${oldGsuri} to ${newPath}`)
}

async function getLabeledOutputLocation(project: string) {
    // TODO: get the labeled output location from firestore project
    return "gs://bird-ml/caples-data/labeled_outputs/"
}

import { NextApiRequest, NextApiResponse } from "next"
import { Storage } from "@google-cloud/storage"
import { NextResponse } from "next/server"
import { CheckSourceInfoResponse } from "@/models/sourceInfos"
import { splitPathIntoBucketAndPath } from "@/utils/gcloud_utils"

export async function POST(request: Request) {
    const body = await request.json()
    return await listSourceGlobs(body.glob)
}

async function listSourceGlobs(glob_pattern: string): Promise<NextResponse> {
    const storage = new Storage()
    try {
        const { bucket, path } = splitPathIntoBucketAndPath(glob_pattern)
        const response = await storage
            .bucket(bucket)
            .getFiles({ matchGlob: path })
        const files = response[0].map((file) => file.name)
        console.log(files)
        const r: CheckSourceInfoResponse = {
            success: true,
            files: files,
        }
        return NextResponse.json(r)
    } catch (e: any) {
        const r: CheckSourceInfoResponse = {
            success: false,
            error: e.message,
            files: [],
        }
        return NextResponse.json(r)
    }
}
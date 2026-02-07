import { Storage } from "@google-cloud/storage"

export function getGoogleStorage() {
    return new Storage({
        credentials: JSON.parse(process.env.GS_SERVICE_ACCOUNT as string),
    })
}

export function splitPathIntoBucketAndPath(url: string): {
    bucket: string
    path: string
} {
    console.log(url)
    const u = url.replace(/^gs:\/\//, "")
    const parts = u.split("/")
    const bucket = parts.shift()
    const path = parts.join("/")
    if (!bucket || !path) {
        throw new Error(
            "Invalid GCS URL, must be in the form gs://bucket-name/path/to/file"
        )
    }
    return { bucket, path }
}

export async function moveFile(
    oldGsuri: string,
    newGsuri: string,
    storage: Storage,
    move = false
) {
    const { bucket: oldBucket, path: oldPath } =
        splitPathIntoBucketAndPath(oldGsuri)
    const { bucket: newBucket, path: newPath } =
        splitPathIntoBucketAndPath(newGsuri)

    const file = storage.bucket(oldBucket).file(oldPath)
    if (move) {
        await file.move(newGsuri)
        console.log(`Successfully moved ${oldGsuri} to ${newGsuri}`)
        return
    }
    await file.copy(newPath)
    console.log(`Successfully copied ${oldGsuri} to ${newPath}`)
}

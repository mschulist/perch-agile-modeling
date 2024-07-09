export function splitPathIntoBucketAndPath(url: string): { bucket: string; path: string } {
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

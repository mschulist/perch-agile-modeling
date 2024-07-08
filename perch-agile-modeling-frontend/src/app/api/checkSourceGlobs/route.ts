import { NextApiRequest, NextApiResponse } from "next";
import { Storage } from "@google-cloud/storage";
import { NextResponse } from "next/server";
import { CheckSourceInfoResponse } from "@/models/sourceInfos";

export async function POST(request: Request) {
  const body = await request.json();
  return await listSourceGlobs(body.glob);
}

async function listSourceGlobs(glob_pattern: string): Promise<NextResponse> {
  const storage = new Storage();
  try {
    const { bucket, glob } = getBucketAndGlob(glob_pattern);
    const response = await storage.bucket(bucket).getFiles({ matchGlob: glob });
    const files = response[0].map((file) => file.name);
    console.log(files);
    const r: CheckSourceInfoResponse = {
      success: true,
      files: files,
    };
    return NextResponse.json(r);
  } catch (e: any) {
    const r: CheckSourceInfoResponse = {
      success: false,
      error: e.message,
      files: [],
    };
    return NextResponse.json(r);
  }
}

function getBucketAndGlob(url: string): { bucket: string; glob: string } {
  console.log(url);
  const u = url.replace(/^gs:\/\//, "");
  const parts = u.split("/");
  const bucket = parts.shift();
  const glob = parts.join("/");
  if (!bucket || !glob) {
    throw new Error(
      "Invalid GCS URL, must be in the form gs://bucket-name/path/to/file"
    );
  }
  return { bucket, glob };
}

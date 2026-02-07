import { NextResponse } from "next/server"
import { getAdminFirestoreDB } from "@/utils/firebaseServerUtils"

const db = getAdminFirestoreDB()

export async function POST(request: Request): Promise<NextResponse> {
    const body = await request.json()
    const email = body.email
    try {
        const project = await getDefaultProject(email)
        return NextResponse.json({ success: true, project })
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message })
    }
}

async function getDefaultProject(email: string): Promise<string> {
    const userInfo = (await db.collection("users").doc(email).get()).data()
    if (!userInfo) {
        throw new Error("User not found")
    }
    return userInfo.defaultProject
}

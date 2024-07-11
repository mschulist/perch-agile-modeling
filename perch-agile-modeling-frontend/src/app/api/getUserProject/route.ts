import { Storage } from "@google-cloud/storage"
import { NextResponse } from "next/server"
import firebaseAdmin from "firebase-admin"
import { cert, ServiceAccount } from "firebase-admin/app"
import { getFirestore } from "firebase-admin/firestore"
import serviceAccount from "../caples-firebase-adminsdk-hp0f6-fcca47250d.json"

/**
 * Initializes the Firebase app with the provided service account credentials.
 */
!firebaseAdmin.apps.length
    ? firebaseAdmin.initializeApp({
          credential: cert(serviceAccount as string | ServiceAccount),
      })
    : firebaseAdmin.app()

const db = getFirestore()

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

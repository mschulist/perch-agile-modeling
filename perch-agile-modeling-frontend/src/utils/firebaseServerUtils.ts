import { ExampleType } from "@/models/existingExamples"
import { ServiceAccount } from "firebase-admin"
import firebaseAdmin from "firebase-admin"
import { cert } from "firebase-admin/app"
import { getFirestore } from "firebase-admin/firestore"

const FIREBASE_SERVICE_ACCOUNT = JSON.parse(
    process.env.FIREBASE_SERVICE_ACCOUNT as string
)

export function getAdminFirestoreDB(): firebaseAdmin.firestore.Firestore {
    /**
     * Initializes the Firebase app with the provided service account credentials.
     */
    !firebaseAdmin.apps.length
        ? firebaseAdmin.initializeApp({
              credential: cert(
                  FIREBASE_SERVICE_ACCOUNT as string | ServiceAccount
              ),
          })
        : firebaseAdmin.app()
    const db = getFirestore()
    return db
}

/**
 * Retrieves the examples path for a given project and example type.
 * @param project - The project name.
 * @param exampleType - The type of example.
 * @returns The examples path.
 * @throws Error if project info or examples path is not found.
 */
export async function getExamplesPath(
    project: string,
    exampleType: ExampleType,
    db: firebaseAdmin.firestore.Firestore
): Promise<string> {
    const projectInfo = (
        await db.collection("projects").doc(project).get()
    ).data()

    console.log(projectInfo)

    if (!projectInfo) {
        throw new Error("Project info not found")
    }

    const examplesPath = projectInfo[exampleType]

    if (!examplesPath) {
        throw new Error("No examples path found for project")
    }

    return examplesPath
}

export async function findAlreadyLabeledFile(
    project: string,
    db: firebaseAdmin.firestore.Firestore
): Promise<string> {
    const projectInfo = (
        await db.collection("projects").doc(project).get()
    ).data()
    const alreadyLabeledFile = projectInfo?.alreadyLabeledFile

    return alreadyLabeledFile
}

export async function getLabeledOutputLocation(
    project: string,
    db: firebaseAdmin.firestore.Firestore
): Promise<string> {
    const projectInfo = (
        await db.collection("projects").doc(project).get()
    ).data()
    const labeledOutputLocation = projectInfo?.labeledOutputs

    return labeledOutputLocation
}

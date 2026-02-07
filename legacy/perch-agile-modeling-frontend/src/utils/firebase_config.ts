"use client"
import { FirebaseApp, initializeApp } from "firebase/app"
import { Analytics, getAnalytics } from "firebase/analytics"
import { GoogleAuthProvider } from "firebase/auth"
import { getFirestore } from "firebase-admin/firestore"
import firebaseAdmin from "firebase-admin"
import { cert, ServiceAccount } from "firebase-admin/app"

const firebaseConfig = {
    apiKey: "AIzaSyAOGWw5LWAXLGH8XimeRxiTpTTfAQoBK5M",
    authDomain: "caples.firebaseapp.com",
    projectId: "caples",
    storageBucket: "caples.appspot.com",
    messagingSenderId: "471006361134",
    appId: "1:471006361134:web:7e64b53452dbb4728491bf",
    measurementId: "G-1215KP9RVW",
}

export function getFirebaseConfig(): FirebaseApp {
    const app = initializeApp(firebaseConfig)
    return app
}

"use client"
import { FirebaseApp, initializeApp } from "firebase/app"
import { Analytics, getAnalytics } from "firebase/analytics"
import { GoogleAuthProvider } from "firebase/auth"
import {
    Firestore,
    getFirestore,
    initializeFirestore,
} from "firebase/firestore"

const firebaseConfig = {
    apiKey: "AIzaSyAOGWw5LWAXLGH8XimeRxiTpTTfAQoBK5M",
    authDomain: "caples.firebaseapp.com",
    projectId: "caples",
    storageBucket: "caples.appspot.com",
    messagingSenderId: "471006361134",
    appId: "1:471006361134:web:7e64b53452dbb4728491bf",
    measurementId: "G-1215KP9RVW",
}

export function getFirebaseConfig(): {
    app: FirebaseApp
    provider: GoogleAuthProvider
    db: Firestore
} {
    const app = initializeApp(firebaseConfig)
    return {
        app,
        provider: new GoogleAuthProvider(),
        db: initializeFirestore(app, { experimentalForceLongPolling: true }),
    }
}

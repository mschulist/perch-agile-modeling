"use client"
import {
    getAuth,
    GoogleAuthProvider,
    signInWithPopup,
    User,
} from "firebase/auth"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getFirebaseConfig } from "@/utils/firebase_config"

const app = getFirebaseConfig()
const provider = new GoogleAuthProvider()

/**
 * Renders the authentication component.
 *
 * @returns The rendered authentication component.
 */
export default function AuthPage() {
    const [user, setUser] = useState<null | User>(null)

    const router = useRouter()

    useEffect(() => {
        const auth = getAuth()
        auth.onAuthStateChanged((user) => {
            setUser(user)
        })
        if (user) {
            router.push("/")
        }
    }, [user, router])

    const signInWithGoogle = async () => {
        const auth = getAuth()
        try {
            const result = await signInWithPopup(auth, provider)
            const user = result.user
            setUser(user)
        } catch (error) {
            console.error(error)
        }
        router.push("/")
    }

    return (
        <div className="text-center mt-8">
            <h1 className="mb-4 text-2xl font-bold">Sign in</h1>
            <button
                className="px-4 py-2 text-base font-medium text-white bg-blue-500 rounded-md cursor-pointer mr-2"
                onClick={signInWithGoogle}
            >
                Sign in with Google
            </button>
        </div>
    )
}

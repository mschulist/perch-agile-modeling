"use client"
import { User, getAuth } from "firebase/auth"
import { useContext, createContext, useState, useEffect } from "react"
import { useRouter } from "next/navigation"

const AuthContext = createContext<User | null>(null)
const ProjectContext = createContext<string | null>(null)

export function Auth(props: { children: React.ReactNode }): React.ReactElement {
    const [user, setUser] = useState<User | null>(null)
    const [project, setProject] = useState<string | null>(null)

    const router = useRouter()

    useEffect(() => {
        fetch("/api/getUserProject", {
            method: "POST",
            body: JSON.stringify({ email: user?.email }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.success) {
                    setProject(data.project)
                }
            })
    }, [user])

    useEffect(() => {
        const auth = getAuth()
        auth.onAuthStateChanged((user) => {
            if (user) {
                setUser(user)
            } else {
                router.push("/login")
            }
        })
    }, [router])

    return (
        <AuthContext.Provider value={user}>
            <ProjectContext.Provider value={project}>
                {props.children}
            </ProjectContext.Provider>
        </AuthContext.Provider>
    )
}

export const useAuth = (): User | null => {
    return useContext(AuthContext)
}

export const useProject = (): string | null => {
    return useContext(ProjectContext)
}

"use client"
import React, { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { User, getAuth } from "firebase/auth"
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuIndicator,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
    NavigationMenuViewport,
} from "@/components/ui/navigation-menu"
import SignOut from "./SignOut"
import { getFirebaseConfig } from "@/utils/firebase_config"
import UserIcon from "./UserIcon"

const { app, provider, db } = getFirebaseConfig()

// TODO: add more paths when more pages are added

const Navbar: React.FC = () => {
    const [user, setUser] = useState<null | User>(null)
    const router = useRouter()
    const auth = getAuth()

    const paths = [
        { href: "/", label: "Home" },
        user && { href: "/sourceInfos", label: "Source Infos" },
        user && { href: "/targetRecordings", label: "Target Recordings" },
    ]

    useEffect(() => {
        const auth = getAuth()
        auth.onAuthStateChanged((user) => {
            setUser(user)
        })
    }, [user])

    return (
        <div className="flex justify-center items-center p-4">
            <NavigationMenu>
                <NavigationMenuList>
                    {paths.map(
                        (path) =>
                            path && (
                                <button
                                    onClick={() => router.push(path.href)}
                                    key={path.href}
                                    className="p-4  rounded-2xl hover:text-red-400 transition-colors duration-300 ease-in-out"
                                >
                                    {path.label}
                                </button>
                            )
                    )}
                </NavigationMenuList>
            </NavigationMenu>

            <NavigationMenu className="absolute right-0 p-4">
                <NavigationMenuList>
                    {user?.displayName && (
                        <p className="text-white">
                            Welcome, {user.displayName}!
                        </p>
                    )}
                    {user?.photoURL && <UserIcon url={user.photoURL} />}
                    <SignOut />
                </NavigationMenuList>
            </NavigationMenu>
        </div>
    )
}

export default Navbar

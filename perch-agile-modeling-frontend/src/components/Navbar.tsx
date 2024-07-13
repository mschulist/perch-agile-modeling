"use client"
import React, {  } from "react"
import { useRouter } from "next/navigation"
import {
    NavigationMenu,
    NavigationMenuList,
} from "@/components/ui/navigation-menu"
import SignOut from "./SignOut"
import { getFirebaseConfig } from "@/utils/firebase_config"
import UserIcon from "./UserIcon"
import { useAuth } from "./Auth"

const { app, provider, db } = getFirebaseConfig()

// TODO: add more paths when more pages are added

const Navbar: React.FC = () => {
    const user = useAuth()
    const router = useRouter()

    const paths = [
        { href: "/", label: "Home" },
        user && { href: "/sourceInfos", label: "Source Infos" },
        user && { href: "/targetRecordings", label: "Target Recordings" },
        user && { href: "/searchResults", label: "Search Results" },
        user && { href: "/labeledOutputs", label: "Labeled Outputs" },
        user && { href: "/annotateRecordings", label: "Annotate Recordings" },
    ]

    return (
        <div className="flex justify-start items-center p-4">
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

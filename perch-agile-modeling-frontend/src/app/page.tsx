import Router from "next/router"
import Link from "next/link"
import HomePage from "@/components/HomePage"

export default function Home() {
    return (
        <div className="flex min-h-screen flex-col p-24">
            <HomePage />
        </div>
    )
}

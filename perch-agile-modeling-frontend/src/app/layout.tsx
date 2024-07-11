import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import Navbar from "@/components/Navbar"
import { Auth } from "@/components/Auth"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
    title: "Perch Agile Modeling",
    description: "",
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body className={inter.className}>
                <Auth>
                    <Navbar />
                    {children}
                </Auth>
            </body>
        </html>
    )
}

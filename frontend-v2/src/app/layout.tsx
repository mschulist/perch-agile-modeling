import type { Metadata } from 'next'
import './globals.css'
import { Auth } from '@/components/auth/Auth'
import { Navbar } from '@/components/navigation/Navbar'

export const metadata: Metadata = {
  title: 'Perch Agile Modeling',
  description: 'For the birds!',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <Auth>
        <body>
          <Navbar />
          {children}
        </body>
      </Auth>
    </html>
  )
}

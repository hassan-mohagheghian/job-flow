import type { Metadata } from 'next'
import { Providers } from '@/app/providers'
import './globals.css'
import { JetBrains_Mono, Merriweather, Inter, Oxanium } from "next/font/google";
import { cn } from "@/shared/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

const merriweatherHeading = Merriweather({subsets:['latin'],variable:'--font-heading'});

const jetbrainsMono = JetBrains_Mono({subsets:['latin'],variable:'--font-mono'});

export const metadata: Metadata = {
  title: 'Job Search Intelligence',
  description: 'AI-powered career platform for any profession',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={cn( inter.variable, "font-mono", jetbrainsMono.variable, merriweatherHeading.variable)}>
      <body>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@100..800&family=Merriweather:wght@400;700;900&display=swap"
          rel="stylesheet"
        />
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}

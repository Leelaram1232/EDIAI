import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "AI Integration Engineer Platform",
  description: "AI-powered Enterprise Integration Engineering Platform for IBM ITX, middleware, EDI, APIs, and mapping technologies",
  keywords: ["IBM ITX", "integration", "AI", "enterprise", "mapping", "EDI", "middleware"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`} suppressHydrationWarning>
      <body className="min-h-screen font-sans antialiased bg-surface-50 dark:bg-surface-950 text-surface-900 dark:text-surface-100">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

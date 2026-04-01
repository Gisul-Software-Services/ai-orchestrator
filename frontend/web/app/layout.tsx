import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Gisul Admin Console",
  description: "Internal admin dashboard for the Gisul AI Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.className} min-h-screen antialiased bg-zinc-950 text-zinc-50`}
      >
        <ThemeProvider>
          <QueryProvider>
            <div className="flex min-h-screen">
              <Sidebar />
              <main className="relative flex-1 overflow-auto bg-zinc-950 bg-[radial-gradient(ellipse_90%_60%_at_50%_-15%,rgba(34,211,238,0.09),transparent_55%),radial-gradient(ellipse_60%_40%_at_100%_50%,rgba(167,139,250,0.06),transparent_50%)]">
                <TopBar />
                <div className="mx-auto w-full max-w-[1400px] px-6 pb-8 pt-4 sm:px-8 sm:pt-6">
                  {children}
                </div>
              </main>
            </div>
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { QueryProvider } from "@/components/providers/QueryProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Model Console",
  description: "Dashboard and playground for the Qwen generation API",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen antialiased`}>
        <QueryProvider>
          <div className="flex min-h-screen">
            <AppSidebar />
            <main className="relative flex-1 overflow-auto bg-zinc-950 bg-[radial-gradient(ellipse_90%_60%_at_50%_-15%,rgba(34,211,238,0.09),transparent_55%),radial-gradient(ellipse_60%_40%_at_100%_50%,rgba(167,139,250,0.06),transparent_50%)] p-6 sm:p-8">
              <div className="mx-auto w-full max-w-[1400px]">{children}</div>
            </main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}

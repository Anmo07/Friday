import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Veritas AI — AI-Powered Truth Engine",
  description: "Real-time multi-agent intelligence platform for fake news detection, truth scoring, and misinformation analysis. Powered by CrewAI, RAG, and Knowledge Graphs.",
  keywords: "fake news detection, truth scoring, AI verification, misinformation, fact checking",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased bg-background text-foreground grid-pattern">
        <Navbar />
        <main className="relative">{children}</main>
      </body>
    </html>
  );
}

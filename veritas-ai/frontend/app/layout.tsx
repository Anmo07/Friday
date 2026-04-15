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
      <body className="antialiased bg-background text-foreground grid-pattern">
        <Navbar />
        <main className="relative">{children}</main>
      </body>
    </html>
  );
}

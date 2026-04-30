import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "FRIDAY — Voice-First AI Assistant",
  description: "Always-on assistant with live voice interaction, interruption handling, OS control, and on-demand verification.",
  keywords: "voice assistant, AI assistant, system control, verification, Friday AI",
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

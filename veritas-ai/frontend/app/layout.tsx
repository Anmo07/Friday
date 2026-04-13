import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Veritas AI Dashboard",
  description: "Real-time Multi-Agent Intelligence Truth Pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIOps Alert Shield // Operational Console",
  description: "Orchestrated, Self-Evolving Hybrid AIOps Alert Verification Platform",
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
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Space+Grotesk:wght@500;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-obsidian text-primaryText antialiased">
        {children}
      </body>
    </html>
  );
}

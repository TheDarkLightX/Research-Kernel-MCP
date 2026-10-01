import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Kernel — Scientific Memory",
  description: "A private workspace for research claims, reproducible evidence and shared scientific memory.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "kokkopi.",
  description: "Kokkopi AI Agent SaaS Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-kokkopi-white text-kokkopi-black flex flex-col selection:bg-kokkopi-teal selection:text-kokkopi-white">
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BookLens",
  description: "A smarter book discovery and recommendation project.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

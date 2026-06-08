import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Korea University Admissions KUA",
  description: "Fast partner portal for Korean university recruitment, applications, and agency management.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

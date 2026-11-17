import type { Metadata } from "next";
import { Dancing_Script } from "next/font/google";
import "./globals.css";

const script = Dancing_Script({ subsets: ["latin"], variable: "--font-script", weight: ["500", "600"] });
const body = Dancing_Script({ subsets: ["latin"], variable: "--font-body", weight: ["500", "600", "700"] });

export const metadata: Metadata = { title: "Ashirwad Industries" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${script.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}

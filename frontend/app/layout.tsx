import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { DocProvider } from "@/lib/store";
import Nav from "@/components/Nav";
import DisclaimerBar from "@/components/DisclaimerBar";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-plex-sans",
  weight: ["400", "500", "600", "700"],
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-plex-mono",
  weight: ["500"],
});

export const metadata: Metadata = {
  title: "LegalLens — Understand the fine print",
  description: "AI-powered legal document assistant. Not a substitute for legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable}`}>
      <body className="font-sans text-[15.5px] leading-[1.55] pb-14 bg-paper text-ink">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[200] focus:bg-ink focus:text-paper focus:px-4 focus:py-2 focus:rounded"
        >
          Skip to main content
        </a>
        <DocProvider>
          <Nav />
          <main id="main-content" className="max-w-[1080px] mx-auto px-7">{children}</main>
          <DisclaimerBar />
        </DocProvider>
      </body>
    </html>
  );
}

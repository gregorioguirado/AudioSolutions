import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "Showfier — Switch console brands in 30 seconds, not 8 hours",
  description:
    "Upload your show file from one mixing console, download it ready for another. First translation free.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body className="flex min-h-screen flex-col">
        <Nav />
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  );
}

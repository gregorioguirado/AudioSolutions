import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "Showfier — Stop Rebuilding Your Shows",
  description:
    "Upload a Yamaha CL/QL show file, download a DiGiCo SD/Quantum translation. 30 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}

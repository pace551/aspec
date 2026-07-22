import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// STK-NEXT-06: next/font self-hosts the font — no external font request, no CLS.
const inter = Inter({ subsets: ["latin"] });

// STK-NEXT-05: Metadata API — title template + description at the root.
export const metadata: Metadata = {
  title: {
    template: "%s · Guestbook",
    default: "Guestbook",
  },
  description:
    "STK-NEXT worked example: one page, one zod-validated server action.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// STK-NEXT-06: next/font self-hosts the font — no external font request, no CLS.
const inter = Inter({ subsets: ["latin"] });

// STK-NEXT-05: Metadata API — title template + description at the root.
export const metadata: Metadata = {
  title: {
    template: "%s · {{PROJECT_NAME}}",
    default: "{{PROJECT_NAME}}",
  },
  description: "{{ONE_LINE_DESCRIPTION}}",
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

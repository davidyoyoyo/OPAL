import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OPAL — Opinion research, made clear",
  description:
    "Explore what people think with structured, evidence-led opinion research.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

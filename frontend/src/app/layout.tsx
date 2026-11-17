import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Academic Intelligence Portal | Student Performance Analysis",
  description: "Enterprise Academic Analytics, OLAP Multidimensional Cubes, Hypothesis Testing, and Student Counseling System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}

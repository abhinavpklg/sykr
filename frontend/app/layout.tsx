import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { JobActionsProvider } from "@/components/JobActionsProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Jobsekr — Every new tech job, within hours",
  description:
    "Job aggregation platform for US-based tech professionals. Fresh jobs from 14+ ATS platforms, updated multiple times daily.",
  openGraph: {
    title: "Jobsekr — Every new tech job, within hours",
    description:
      "Fresh jobs from Greenhouse, Lever, Ashby, and 11 more ATS platforms.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.className} bg-[#0d1117] text-gray-200 min-h-screen antialiased`}
      >
        <JobActionsProvider>{children}</JobActionsProvider>
      </body>
    </html>
  );
}
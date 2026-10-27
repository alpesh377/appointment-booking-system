import type { Metadata } from "next";

import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "Appointly — appointment booking",
  description: "Book service providers, manage availability and oversee appointments.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background">
        <Providers>
          <SiteHeader />
          <main className="page-container py-8">{children}</main>
          <footer className="page-container border-t py-6 text-sm text-muted-foreground">
            Appointly — appointments are shown in the provider&apos;s local timezone.
          </footer>
        </Providers>
        <Toaster position="top-center" />
      </body>
    </html>
  );
}

import type { Metadata } from "next";

import { AppProvider } from "@/components/app-context";
import { AppShell } from "@/components/app-shell";
import { site } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: site.name, template: `%s | ${site.name}` },
  description:
    "Capture what a departing employee knows through a graph-driven exit interview, then build a handover plan for each person taking over their work.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="h-full font-sans">
        <AppProvider>
          <AppShell>{children}</AppShell>
        </AppProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { data } from "@/lib/data";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: { default: "BharatBench", template: "%s · BharatBench" },
  description: "A public benchmark of how well LLMs handle real Indian tasks: GST and tax, Hinglish support, documents, law and payments.",
};

const nav = [
  { href: "/", label: "Leaderboard" },
  { href: "/#hinglish-gap", label: "Hinglish gap" },
  { href: "/methodology/", label: "Methodology" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
            <Link href="/" className="text-lg font-semibold tracking-tight">BharatBench</Link>
            <nav aria-label="Main" className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="py-1 hover:text-fg">{n.label}</Link>
              ))}
            </nav>
          </div>
          <nav aria-label="Categories" className="mx-auto max-w-5xl overflow-x-auto px-4 pb-2">
            <ul className="flex gap-2 whitespace-nowrap text-xs">
              {data.categories.map((c) => (
                <li key={c.id}>
                  <Link href={`/categories/${c.slug}/`} className="inline-block rounded-full border border-line px-3 py-1 text-muted hover:text-fg">{c.title}</Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-5xl px-4 pb-10 pt-4 text-xs text-muted">
          Run {data.run_id} · last updated {formatDate(data.last_updated)} ·{" "}
          <Link href="/methodology/" className="underline">How this works</Link>
        </footer>
      </body>
    </html>
  );
}

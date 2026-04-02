"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

const steps = [
  { title: "Upload", desc: "Sync your docs, FAQs, and knowledge bases securely." },
  { title: "Embed", desc: "Drop the chatbot widget on any page with one snippet." },
  { title: "Answer", desc: "Serve precise answers with RAG tuned to your domain." }
];

const features = [
  { title: "RAG-native", desc: "Retrieval-augmented answers grounded in your content." },
  { title: "Secure Isolation", desc: "Org-level segregation with least-privilege access." },
  { title: "Domain Control", desc: "Allowlist sources and throttle responses per space." }
];

const useCases = [
  { title: "Customer Support", desc: "Deflect tickets with instant, accurate responses." },
  { title: "Internal Docs", desc: "Give teams a single, trusted knowledge assistant." },
  { title: "Product FAQs", desc: "Keep answers consistent across sites and channels." }
];

export default function LandingPage() {
  const { isAuthenticated, isReady } = useAuth();

  return (
    <main className="min-h-screen bg-white text-slate-900">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-20 px-6 py-10 md:px-10 md:py-16">
        <header className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white/70 px-5 py-4 shadow-sm backdrop-blur">
          <Link href="/" className="text-lg font-semibold text-slate-900">
            RAGChat
          </Link>
          <div className="flex items-center gap-3">
            {isReady && !isAuthenticated && (
              <Link
                href="/login"
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                Login
              </Link>
            )}
            {isReady && isAuthenticated ? (
              <Link
                href="/dashboard"
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                Dashboard
              </Link>
            ) : (
              <Link
                href="/signup"
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                Get Started
              </Link>
            )}
          </div>
        </header>

        <section className="grid gap-10 md:grid-cols-2 md:items-center">
          <div className="space-y-6">
            <p className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-500">
              AI Chatbot SaaS
            </p>
            <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">
              Plug-and-Play AI Chatbot for Your Website
            </h1>
            <p className="text-lg text-slate-600 md:text-xl">
              RAG-based answers grounded in your content—upload knowledge, embed once, and deliver
              fast, secure responses with full domain control.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/signup"
                className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                Get Started
              </Link>
              <Link
                href="/demo"
                className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
              >
                View Demo
              </Link>
            </div>
            <div className="flex flex-wrap gap-4 text-sm text-slate-500">
              <span className="rounded-full bg-slate-100 px-3 py-1">RAG-native</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">Secure by default</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">5-minute embed</span>
            </div>
          </div>
          <div className="relative overflow-hidden rounded-2xl border border-slate-100 bg-slate-50 p-6 shadow-sm">
            <div className="absolute -left-16 -top-16 h-32 w-32 rounded-full bg-gradient-to-br from-indigo-100 to-slate-200 opacity-70 blur-3xl" />
            <div className="absolute -bottom-10 -right-10 h-40 w-40 rounded-full bg-gradient-to-tr from-slate-200 to-emerald-100 opacity-60 blur-3xl" />
            <div className="relative grid gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
                    AI
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Website Assistant</p>
                    <p className="text-xs text-slate-500">Always-on, always-grounded</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2 text-sm text-slate-700">
                  <p>
                    "Upload docs, embed the widget, and your customers get instant answers powered by
                    retrieval."
                  </p>
                  <p className="text-xs text-slate-500">No hallucinations. No maintenance burden.</p>
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Live snippet
                </p>
                <pre className="mt-3 overflow-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
{`<script src="https://cdn.ragchat.ai/widget.js"
  data-org="acme"
  data-domain-allowlist="acme.com"
></script>`}
                </pre>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-10 rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">How it works</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {steps.map((step) => (
              <div
                key={step.title}
                className="rounded-xl border border-slate-100 bg-slate-50 p-6 shadow-xs"
              >
                <h3 className="text-lg font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-10 rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">Key features</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-900">{feature.title}</h3>
                <p className="text-sm text-slate-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-10 rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">Use cases</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {useCases.map((item) => (
              <div key={item.title} className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
                <p className="text-sm text-slate-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

"use client";

import { isAxiosError } from "axios";
import useSWR from "swr";
import { AppHeader } from "@/components/AppHeader";
import { fetcher } from "@/lib/api";

type DashboardSummary = {
  total_documents: number;
  documents_completed: number;
  documents_processing: number;
  documents_failed: number;
  total_tokens_used: number;
  total_chunks: number;
};

const cards: Array<{ key: keyof DashboardSummary; title: string }> = [
  { key: "total_documents", title: "Total Files" },
  { key: "documents_completed", title: "Completed" },
  { key: "documents_processing", title: "Processing" },
  { key: "documents_failed", title: "Failed" },
  { key: "total_tokens_used", title: "Total Tokens Used" },
  { key: "total_chunks", title: "Total Chunks" }
];

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<DashboardSummary>("/dashboard", fetcher);
  const errorMessage = isAxiosError(error)
    ? error.response?.data?.detail || "Failed to load dashboard analytics."
    : "Failed to load dashboard analytics.";

  return (
    <div className="flex w-full flex-col gap-6">
      <AppHeader title="Dashboard" eyebrow="Overview" />
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        {cards.map((card) => (
          <article
            key={card.key}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">{card.title}</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
              {isLoading ? "..." : data?.[card.key] ?? 0}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { AppHeader } from "@/components/AppHeader";
import { useAuth } from "@/lib/auth";

type DocumentStatus = "queued" | "processing" | "succeeded" | "failed";

type DocumentItem = {
  id: string;
  filename: string;
  status: DocumentStatus;
  error_message?: string | null;
};

type DocumentsResponse = {
  items: DocumentItem[];
};

function shouldPoll(items: DocumentItem[] | undefined) {
  if (!items) return false;
  return items.some((item) => item.status === "queued" || item.status === "processing");
}

export default function DocumentsPage() {
  const { logout } = useAuth();

  const { data, error, isLoading } = useSWR<DocumentsResponse>("/documents", fetcher, {
    refreshInterval: (latest) => (shouldPoll(latest?.items) ? 7000 : 0)
  });

  const items = useMemo(() => data?.items ?? [], [data]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
      <AppHeader title="Documents" onLogout={logout} />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Ingestion status</h2>
          <span className="text-xs text-slate-500">
            {isLoading ? "Loading..." : `${items.length} document${items.length === 1 ? "" : "s"}`}
          </span>
        </div>

        {error && <p className="mt-4 text-sm text-red-600">Failed to load documents.</p>}

        {!isLoading && items.length === 0 && (
          <p className="mt-4 text-sm text-slate-600">No documents uploaded yet.</p>
        )}

        {items.length > 0 && (
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Filename</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((doc) => (
                  <tr key={doc.id} className="bg-white">
                    <td className="px-4 py-3 font-medium text-slate-900">{doc.filename}</td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          doc.status === "succeeded"
                            ? "rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700"
                            : doc.status === "failed"
                            ? "rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-600"
                            : doc.status === "processing"
                            ? "rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700"
                            : "rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600"
                        }
                      >
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {doc.status === "failed" ? doc.error_message || "Unknown error" : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

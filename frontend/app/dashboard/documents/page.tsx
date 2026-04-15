"use client";

import { useMemo, useState } from "react";
import { isAxiosError } from "axios";
import useSWR from "swr";
import { AppHeader } from "@/components/AppHeader";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ToastMessage } from "@/components/ToastMessage";
import { api, fetcher } from "@/lib/api";

type DocumentStatus = "queued" | "processing" | "succeeded" | "failed";

type DocumentItem = {
  id: string;
  filename: string;
  status: DocumentStatus;
  error_message?: string | null;
  created_at: string;
};

type DocumentsResponse = {
  items: DocumentItem[];
};

type ToastState = {
  kind: "success" | "error";
  message: string;
} | null;

function shouldPoll(items: DocumentItem[] | undefined) {
  if (!items) return false;
  return items.some((item) => item.status === "queued" || item.status === "processing");
}

function formatStatus(status: DocumentStatus) {
  if (status === "succeeded") return "completed";
  return status;
}

function formatCreatedAt(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export default function DocumentsPage() {
  const { data, error, isLoading, mutate } = useSWR<DocumentsResponse>("/documents", fetcher, {
    refreshInterval: (latest) => (shouldPoll(latest?.items) ? 7000 : 0)
  });
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null);
  const [toast, setToast] = useState<ToastState>(null);
  const items = useMemo(() => data?.items ?? [], [data]);
  const listError = isAxiosError(error)
    ? error.response?.data?.detail || "Failed to load documents."
    : "Failed to load documents.";

  const getActionLabel = (status: DocumentStatus) =>
    status === "failed" ? "Retry" : status === "succeeded" ? "Re-ingest" : "Re-ingest";

  const handleReingest = async (doc: DocumentItem) => {
    setToast(null);
    setActiveDocId(doc.id);
    try {
      const response = await api.post<{ detail?: string }>(`/documents/${doc.id}/reingest`);
      setToast({
        kind: "success",
        message: response.data.detail || `${doc.filename} re-ingested successfully.`
      });
      await mutate();
    } catch (actionError: unknown) {
      const message = isAxiosError(actionError)
        ? actionError.response?.data?.detail || "Failed to re-ingest document."
        : "Failed to re-ingest document.";
      setToast({ kind: "error", message });
    } finally {
      setActiveDocId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setToast(null);
    setActiveDocId(deleteTarget.id);
    try {
      const response = await api.delete<{ detail?: string }>(`/documents/${deleteTarget.id}`);
      setToast({
        kind: "success",
        message: response.data.detail || `${deleteTarget.filename} deleted successfully.`
      });
      setDeleteTarget(null);
      await mutate();
    } catch (actionError: unknown) {
      const message = isAxiosError(actionError)
        ? actionError.response?.data?.detail || "Failed to delete document."
        : "Failed to delete document.";
      setToast({ kind: "error", message });
    } finally {
      setActiveDocId(null);
    }
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <AppHeader title="Documents" eyebrow="Knowledge Base" />

      {toast ? <ToastMessage kind={toast.kind} message={toast.message} /> : null}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Ingestion status</h2>
          <span className="text-xs text-slate-500">
            {isLoading ? "Loading..." : `${items.length} document${items.length === 1 ? "" : "s"}`}
          </span>
        </div>

        {error && <p className="mt-4 text-sm text-red-600">{listError}</p>}

        {!isLoading && items.length === 0 && (
          <p className="mt-4 text-sm text-slate-600">No documents uploaded yet.</p>
        )}

        {items.length > 0 && (
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Filename</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Error</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((doc) => (
                  <tr key={doc.id} className="bg-white">
                    <td className="px-4 py-3 font-medium text-slate-900">{doc.filename}</td>
                    <td className="px-4 py-3 text-slate-500">{formatCreatedAt(doc.created_at)}</td>
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
                        {formatStatus(doc.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {doc.status === "failed" ? doc.error_message || "Unknown error" : "-"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => handleReingest(doc)}
                          disabled={activeDocId === doc.id}
                          className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {activeDocId === doc.id ? "Working..." : getActionLabel(doc.status)}
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(doc)}
                          disabled={activeDocId === doc.id}
                          className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-300"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {deleteTarget ? (
        <ConfirmDialog
          title="Delete document?"
          description="Are you sure? This will delete all embeddings."
          confirmLabel="Delete"
          loading={activeDocId === deleteTarget.id}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      ) : null}
    </div>
  );
}

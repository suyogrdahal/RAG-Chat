"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { AppHeader } from "@/components/AppHeader";
import { useAuth } from "@/lib/auth";
import { fetcher } from "@/lib/api";

type SourceEntry = Record<string, unknown>;

type ChatLogDetail = {
  id: string;
  session_id: string | null;
  query_text: string;
  response_text: string;
  confidence: number | null;
  sources: SourceEntry[];
  created_at: string;
};

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export default function ChatLogDetailPage() {
  const { logout } = useAuth();
  const params = useParams();
  const rawId = params?.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { data, error, isLoading } = useSWR<ChatLogDetail>(id ? `/chat-logs/${id}` : null, fetcher);

  if (!id) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
        <AppHeader title="Chat Log" onLogout={logout} />
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-red-600">Invalid log id.</p>
        </section>
      </main>
    );
  }

  if (error) {
    const detail = (error as { status?: number }).status;
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
        <AppHeader title="Chat Log" onLogout={logout} />
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-red-600">
            {detail === 404 ? "Chat log not found." : "Failed to load chat log."}
          </p>
          <Link href="/dashboard/chat-logs" className="mt-4 inline-block text-sm text-sky-700 underline">
            Back to logs
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
      <AppHeader title="Chat Log" onLogout={logout} />
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Chat log details</h2>
          <span className="text-sm text-slate-500">
            {isLoading ? "Loading..." : data ? formatDate(data.created_at) : "--"}
          </span>
        </div>

        <div className="mt-4 space-y-3 text-sm text-slate-700">
          <div>
            <span className="font-semibold text-slate-900">Session:</span> {data?.session_id || "-"}
          </div>
          <div>
            <span className="font-semibold text-slate-900">Confidence:</span>{" "}
            {data?.confidence == null ? "-" : data.confidence.toFixed(2)}
          </div>
          <div>
            <span className="font-semibold text-slate-900">Query:</span>
            <div className="mt-2 whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3">
              {data?.query_text}
            </div>
          </div>
          <div>
            <span className="font-semibold text-slate-900">Response:</span>
            <div className="mt-2 whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3">
              {data?.response_text}
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="text-sm font-semibold text-slate-900">Sources</h3>
          {data?.sources && data.sources.length > 0 ? (
            <pre className="mt-3 overflow-auto rounded-md border border-slate-200 bg-slate-900 p-3 text-xs text-slate-100">
              {JSON.stringify(data.sources, null, 2)}
            </pre>
          ) : (
            <p className="mt-3 text-sm text-slate-600">No sources were attached to this answer.</p>
          )}
        </div>

        <div className="mt-6">
          <Link href="/dashboard/chat-logs" className="text-sm text-sky-700 underline">
            Back to logs
          </Link>
        </div>
      </section>
    </main>
  );
}
"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { fetcher } from "@/lib/api";
import { AppHeader } from "@/components/AppHeader";

type ChatLogItem = {
  id: string;
  session_id: string | null;
  query_text: string;
  response_text: string;
  confidence: number | null;
  sources: Record<string, unknown>[];
  created_at: string;
};

type ChatLogListResponse = {
  items: ChatLogItem[];
  limit: number;
  offset: number;
  total: number;
};

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function responseSummary(response: string): string {
  const trimmed = response.trim();
  if (trimmed.length <= 160) {
    return trimmed;
  }
  return `${trimmed.slice(0, 157).trimEnd()}...`;
}

export default function ChatLogsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const limit = Math.max(1, Math.min(100, Number(searchParams.get("limit") || 25)));
  const offset = Math.max(0, Number(searchParams.get("offset") || 0));
  const search = searchParams.get("search") || "";
  const sessionIdFilter = searchParams.get("session_id") || "";
  const dateFrom = searchParams.get("date_from") || "";
  const dateTo = searchParams.get("date_to") || "";

  const listParams = useMemo(() => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (search.trim()) params.set("search", search.trim());
    if (sessionIdFilter.trim()) params.set("session_id", sessionIdFilter.trim());
    if (dateFrom.trim()) params.set("date_from", dateFrom.trim());
    if (dateTo.trim()) params.set("date_to", dateTo.trim());
    return params.toString();
  }, [limit, offset, search, sessionIdFilter, dateFrom, dateTo]);

  const { data, error, isLoading } = useSWR<ChatLogListResponse>(
    `/chat-logs?${listParams}`,
    fetcher
  );

  const nextOffset = offset + limit;
  const prevOffset = Math.max(0, offset - limit);

  const hasNext = Number(data?.total ?? 0) > nextOffset;
  const items = useMemo(() => data?.items ?? [], [data]);

  const toPage = (nextOffsetValue: number) => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(Math.max(0, nextOffsetValue)));
    if (search.trim()) params.set("search", search.trim());
    if (sessionIdFilter.trim()) params.set("session_id", sessionIdFilter.trim());
    if (dateFrom.trim()) params.set("date_from", dateFrom.trim());
    if (dateTo.trim()) params.set("date_to", dateTo.trim());
    router.push(`/dashboard/chat-logs?${params.toString()}`);
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <AppHeader title="Chat Logs" eyebrow="Activity" />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Recent chats</h2>
        <p className="mt-1 text-sm text-slate-600">
          Tenant-scoped interactions with logged user-visible query and response.
        </p>

        <form
          className="mt-4 flex flex-wrap gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const nextSearch = String(formData.get("search") || "").trim();
            const nextSession = String(formData.get("session_id") || "").trim();
            const nextDateFrom = String(formData.get("date_from") || "").trim();
            const nextDateTo = String(formData.get("date_to") || "").trim();
            const params = new URLSearchParams();
            params.set("limit", String(limit));
            params.set("offset", "0");
            if (nextSearch) params.set("search", nextSearch);
            if (nextSession) params.set("session_id", nextSession);
            if (nextDateFrom) params.set("date_from", nextDateFrom);
            if (nextDateTo) params.set("date_to", nextDateTo);
            router.push(`/dashboard/chat-logs?${params.toString()}`);
          }}
        >
          <input
            type="text"
            name="search"
            defaultValue={search}
            placeholder="Search query or response"
            className="w-full flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-slate-500"
          />
          <input
            type="text"
            name="session_id"
            defaultValue={sessionIdFilter}
            placeholder="Filter by session id"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-slate-500 md:w-72"
          />
          <input
            type="datetime-local"
            name="date_from"
            defaultValue={dateFrom}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-slate-500 md:w-72"
          />
          <input
            type="datetime-local"
            name="date_to"
            defaultValue={dateTo}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-slate-500 md:w-72"
          />
          <button
            type="submit"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
          >
            Apply
          </button>
        </form>

        {error && <p className="mt-4 text-sm text-red-600">Failed to load chat logs.</p>}
        {!isLoading && items.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">No chat logs found.</p>
        ) : null}

        {items.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[780px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Session</th>
                  <th className="px-4 py-3">Query</th>
                  <th className="px-4 py-3">Response</th>
                  <th className="px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id} className="bg-white">
                    <td className="px-4 py-3 text-slate-600">{formatDate(item.created_at)}</td>
                    <td className="px-4 py-3 text-slate-600">
                      <Link
                        href={`/dashboard/chat-logs/${item.id}`}
                        className="rounded-md text-sky-700 underline underline-offset-2 hover:text-sky-900"
                      >
                        {item.session_id || "-"}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <Link href={`/dashboard/chat-logs/${item.id}`} className="hover:text-sky-700 hover:underline">
                        {item.query_text}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      <Link href={`/dashboard/chat-logs/${item.id}`} className="hover:text-sky-700 hover:underline">
                        {responseSummary(item.response_text)}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {item.confidence === null ? "-" : item.confidence.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-slate-600">
            {isLoading
              ? "Loading..."
              : `${data?.total ?? 0} total log${(data?.total ?? 0) === 1 ? "" : "s"}`}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => toPage(prevOffset)}
              disabled={offset === 0}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => toPage(nextOffset)}
              disabled={!hasNext}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

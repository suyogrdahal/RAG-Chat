"use client";

import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { api, fetcher } from "@/lib/api";
import { AppHeader } from "@/components/AppHeader";
import { useAuth } from "@/lib/auth";
import { normalizeDomain, widgetSnippet } from "@/lib/widget";

type WidgetConfigResponse = {
  widget_public_key: string;
  allowed_domains: string[];
  theme?: Record<string, unknown> | null;
};

export default function WidgetPage() {
  const { logout } = useAuth();
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string>("");

  const {
    data: config,
    error: configError,
    isLoading
  } = useSWR<WidgetConfigResponse>("/widget/config", fetcher, {
    onSuccess: (next) => {
      setEditing(next.allowed_domains.join("\n"));
    }
  });

  const snippet = useMemo(
    () => (config?.widget_public_key ? widgetSnippet(config.widget_public_key) : ""),
    [config?.widget_public_key]
  );

  const handleCopy = async () => {
    if (!snippet) return;
    await navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const parsedDomains = useMemo(() => {
    return editing
      .split("\n")
      .map((line) => normalizeDomain(line))
      .filter(Boolean);
  }, [editing]);

  const handleSaveDomains = async () => {
    setSaveError("");
    setSaving(true);
    try {
      await api.put("/widget/domains", { allowed_domains: parsedDomains });
      await mutate("/widget/config");
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "response" in err) {
        const maybeResponse = err as {
          response?: { data?: { detail?: string } };
        };
        setSaveError(maybeResponse.response?.data?.detail || "Failed to save domains");
      } else {
        setSaveError("Failed to save domains");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
      <AppHeader title="Widget" onLogout={logout} />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Embed snippet</h2>
        <p className="mt-1 text-sm text-slate-600">
          Uses your public widget identifier only. No private keys are exposed.
        </p>
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <pre className="whitespace-pre-wrap break-all text-sm text-slate-800">
            {snippet || "Loading..."}
          </pre>
        </div>
        <button
          onClick={handleCopy}
          disabled={!snippet}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {copied ? "Copied" : "Copy to clipboard"}
        </button>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Domain whitelist</h2>
        <p className="mt-1 text-sm text-slate-600">
          One domain per line, example: https://example.com
        </p>
        <textarea
          value={editing}
          onChange={(event) => setEditing(event.target.value)}
          className="mt-4 min-h-40 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-slate-500"
          placeholder="https://example.com"
        />
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSaveDomains}
            disabled={saving || isLoading}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {saving ? "Saving..." : "Save domains"}
          </button>
          {saveError ? <p className="text-sm text-red-600">{saveError}</p> : null}
        </div>
        <div className="mt-4 space-y-2 text-sm text-slate-700">
          {config?.allowed_domains?.length ? (
            config.allowed_domains.map((domain) => (
              <div
                key={domain}
                className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2"
              >
                {domain}
              </div>
            ))
          ) : (
            <p className="text-slate-500">No domains configured.</p>
          )}
        </div>
      </section>
      {configError ? (
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to load widget config.
        </p>
      ) : null}
    </main>
  );
}

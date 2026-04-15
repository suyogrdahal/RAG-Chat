"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { uploadDocument } from "@/lib/api";
import { AppHeader } from "@/components/AppHeader";

const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["application/pdf", "text/plain"];

function validateFile(file: File | null) {
  if (!file) return "Please select a file.";
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "Only PDF and TXT files are allowed.";
  }
  if (file.size > MAX_SIZE_BYTES) {
    return "File is too large. Max size is 10MB.";
  }
  return null;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [loading, setLoading] = useState(false);

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const next = e.target.files?.[0] ?? null;
    setFile(next);
    setError(null);
    setSuccess(null);
    setProgress(0);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    if (!file) return;

    setLoading(true);
    setProgress(0);
    try {
      await uploadDocument(file, (p) => setProgress(p));
      setSuccess("Upload successful.");
      setFile(null);
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "Upload failed. Please try again.";
      setError(typeof message === "string" ? message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <AppHeader title="Upload" eyebrow="Ingestion" />
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Upload documents</h2>
        <p className="text-sm text-slate-600">
          Upload PDF or TXT files. Server-side validation still applies.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            File
            <input
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={onFileChange}
              className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-slate-800"
            />
          </label>

          <div className="text-xs text-slate-500">
            Max size: 10MB. Accepted: PDF, TXT.
          </div>
        </div>

        {loading && (
          <div className="mt-4">
            <div className="h-2 w-full rounded-full bg-slate-200">
              <div
                className="h-2 rounded-full bg-slate-900 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">{progress}%</p>
          </div>
        )}

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        {success && <p className="mt-4 text-sm text-emerald-600">{success}</p>}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>
    </div>
  );
}

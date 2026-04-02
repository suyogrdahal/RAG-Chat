"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type ValidationErrors = Record<string, string>;

function toSlug(name: string) {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "");
}

export function SignupForm() {
  const router = useRouter();

  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<ValidationErrors>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setFieldErrors({});

    if (!orgName || !email || !password) {
      setFieldErrors({
        ...(orgName ? {} : { org_name: "Organization is required." }),
        ...(email ? {} : { email: "Email is required." }),
        ...(password ? {} : { password: "Password is required." })
      });
      return;
    }

    const base = api.defaults.baseURL ?? "";
    const isLocalhost = base.includes("localhost") || base.includes("127.0.0.1");
    if (base && !base.startsWith("https://") && !isLocalhost) {
      setError("API must be served over HTTPS for signup.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/auth/signup", {
        org_name: orgName,
        org_slug: toSlug(orgName) || undefined,
        email,
        password
      });

      setSuccess("Signup successful");
      setLoading(false);
      setPassword("");
      setTimeout(() => router.push("/login"), 800);
    } catch (err: any) {
      const backendMessage =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        "Unable to sign up. Please check your details and try again.";

      const backendFieldErrors =
        err?.response?.data?.errors ||
        (Array.isArray(err?.response?.data?.detail)
          ? Object.fromEntries(
              err.response.data.detail
                .filter((d: any) => Array.isArray(d.loc) && d.loc.length >= 2)
                .map((d: any) => [d.loc[1], d.msg])
            )
          : null);

      if (backendFieldErrors && typeof backendFieldErrors === "object") {
        setFieldErrors(backendFieldErrors as ValidationErrors);
      } else {
        setFieldErrors({});
      }

      setError(typeof backendMessage === "string" ? backendMessage : String(backendMessage));
      setLoading(false);
      setPassword("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-700">
          Organization name
          <input
            type="text"
            required
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
          />
        </label>
        {fieldErrors.org_name && <p className="text-xs text-red-600">{fieldErrors.org_name}</p>}
      </div>

      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-700">
          Admin email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
          />
        </label>
        {fieldErrors.email && <p className="text-xs text-red-600">{fieldErrors.email}</p>}
      </div>

      <div className="space-y-1">
        <label className="block text-sm font-medium text-slate-700">
          Password
          <input
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
          />
        </label>
        {fieldErrors.password && <p className="text-xs text-red-600">{fieldErrors.password}</p>}
      </div>

      {success && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        {loading ? "Creating account..." : "Create account"}
      </button>

      <p className="text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-slate-900 hover:underline">
          Log in
        </Link>
      </p>
    </form>
  );
}

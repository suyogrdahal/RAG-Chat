"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { useAuth } from "@/lib/auth";
import { BackButton } from "@/components/BackButton";
import { FormErrorMessage } from "@/components/FormErrorMessage";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isReady } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isReady && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isReady, isAuthenticated, router]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      const message = isAxiosError(err)
        ? err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "Login failed"
        : err instanceof Error
        ? err.message
        : "Login failed";

      setError(typeof message === "string" ? message : "Login failed");
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto flex w-full max-w-md flex-col gap-6">
        <BackButton />

        <div className="w-full rounded-2xl bg-white p-8 shadow-xl ring-1 ring-slate-100">
          <h1 className="text-2xl font-semibold text-slate-900">Sign in</h1>
          <p className="mt-1 text-sm text-slate-500">Use your admin credentials.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
              />
            </label>

            <label className="block text-sm font-medium text-slate-700">
              Password
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
              />
            </label>

            {error && <FormErrorMessage message={error} />}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="font-semibold text-slate-900 hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}

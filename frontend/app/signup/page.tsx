"use client";

import Link from "next/link";
import { SignupForm } from "@/components/SignupForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-xl rounded-2xl bg-white p-10 shadow-xl ring-1 ring-slate-100">
        <div className="mb-8 space-y-2">
          <p className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-500">
            Organization onboarding
          </p>
          <h1 className="text-3xl font-semibold text-slate-900">Create your workspace</h1>
          <p className="text-sm text-slate-600">
            Set up your organization admin account to start deploying the chatbot.
          </p>
        </div>

        <SignupForm />

        <div className="mt-6 text-center text-xs text-slate-500">
          By continuing you agree to our{" "}
          <Link href="/terms" className="underline">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="underline">
            Privacy
          </Link>
          .
        </div>
      </div>
    </main>
  );
}

"use client";

import { AppHeader } from "@/components/AppHeader";
import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const { logout } = useAuth();
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
      <AppHeader title="Dashboard" onLogout={logout} />
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Welcome back</h2>
          <p className="text-sm text-slate-500">You are authenticated.</p>
        </div>
      </section>
    </main>
  );
}

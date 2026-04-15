"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { DashboardSidebar } from "@/components/DashboardSidebar";

export default function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isReady } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isReady && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isReady, isAuthenticated, router]);

  if (!isReady) return null;
  if (!isAuthenticated) return null;
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen flex-col md:flex-row">
        <DashboardSidebar />
        <main className="flex-1">
          <div className="mx-auto flex w-full max-w-7xl flex-col px-4 py-6 sm:px-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

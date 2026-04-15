"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/chat-logs", label: "Chat Logs" },
  { href: "/dashboard/upload", label: "Upload" },
  { href: "/dashboard/documents", label: "Documents" },
  { href: "/dashboard/widget", label: "Widget" }
];

export function DashboardSidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <aside className="w-full border-b border-slate-200 bg-white px-4 py-4 md:min-h-screen md:w-64 md:border-b-0 md:border-r md:px-5">
      <div className="flex h-full flex-col gap-6">
        <div>
          <Link href="/dashboard" className="text-lg font-semibold text-slate-900">
            RAGChat
          </Link>
          <p className="mt-1 text-sm text-slate-500">Workspace admin</p>
        </div>

        <nav className="flex flex-wrap gap-2 md:flex-col">
          {navItems.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={logout}
          className="mt-auto rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}

import Link from "next/link";

type AppHeaderProps = {
  title: string;
  showNav?: boolean;
  onLogout?: () => void;
};

export function AppHeader({ title, showNav = true, onLogout }: AppHeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex items-center gap-6">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {showNav && (
            <nav className="flex items-center gap-3 text-sm text-slate-600">
            <Link href="/dashboard" className="rounded-md px-2 py-1 hover:bg-slate-100">
              Dashboard
            </Link>
            <Link
              href="/dashboard/chat-logs"
              className="rounded-md px-2 py-1 hover:bg-slate-100"
            >
              Chat Logs
            </Link>
            <Link
              href="/dashboard/upload"
              className="rounded-md px-2 py-1 hover:bg-slate-100"
            >
              Upload
            </Link>
            <Link
              href="/dashboard/documents"
              className="rounded-md px-2 py-1 hover:bg-slate-100"
            >
              Documents
            </Link>
            <Link
              href="/dashboard/widget"
              className="rounded-md px-2 py-1 hover:bg-slate-100"
            >
              Widget
            </Link>
          </nav>
        )}
      </div>
      {onLogout && (
        <button
          onClick={onLogout}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          Log out
        </button>
      )}
    </header>
  );
}

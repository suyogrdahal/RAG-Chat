type AppHeaderProps = {
  title: string;
  eyebrow?: string;
};

export function AppHeader({ title, eyebrow }: AppHeaderProps) {
  return (
    <header className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
      {eyebrow ? (
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          {eyebrow}
        </p>
      ) : null}
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">{title}</h1>
    </header>
  );
}

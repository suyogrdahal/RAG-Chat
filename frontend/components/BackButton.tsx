"use client";

import { useRouter } from "next/navigation";

type BackButtonProps = {
  href?: string;
  className?: string;
};

export function BackButton({ href = "/", className = "" }: BackButtonProps) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push(href)}
      className={`inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 ${className}`.trim()}
      aria-label="Go back"
    >
      <span aria-hidden="true" className="text-base leading-none">
        ←
      </span>
      <span>Back</span>
    </button>
  );
}

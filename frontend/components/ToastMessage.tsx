"use client";

type ToastMessageProps = {
  kind: "success" | "error";
  message: string;
};

export function ToastMessage({ kind, message }: ToastMessageProps) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 text-sm shadow-sm ${
        kind === "success"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-red-200 bg-red-50 text-red-700"
      }`}
      role="status"
    >
      {message}
    </div>
  );
}

"use client";

type FormErrorMessageProps = {
  message: string;
  className?: string;
};

export function FormErrorMessage({ message, className = "" }: FormErrorMessageProps) {
  return (
    <p
      role="alert"
      className={`rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 ${className}`.trim()}
    >
      {message}
    </p>
  );
}

"use client";

function escapeAttribute(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

export function widgetSnippet(publicOrgIdentifier: string) {
  return `<aichatbot org-id="${escapeAttribute(publicOrgIdentifier)}"></aichatbot>`;
}

export function normalizeDomain(domain: string): string {
  return domain.trim().toLowerCase();
}

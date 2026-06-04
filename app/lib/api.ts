export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  return process.env.NEXT_PUBLIC_API_URL || "";
}

export function apiUrl(path: string): string {
  const base = getApiBase();
  return `${base}${path}`;
}

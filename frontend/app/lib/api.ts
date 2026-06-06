import { CLIENT_API_BASE } from "./config";

export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  return CLIENT_API_BASE;
}

export function apiUrl(path: string): string {
  const base = getApiBase();
  return `${base}${path}`;
}

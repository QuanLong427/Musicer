import path from "path";

/**
 * Frontend environment configuration.
 *
 * All env vars are read here — no hardcoded fallbacks scattered in route files.
 * Next.js loads .env from project root automatically.
 *
 * IMPORTANT: This module is imported by both server (route handlers) and
 * client code. Non-NEXT_PUBLIC vars are undefined on the client — only use
 * them in server-side code (route handlers, server actions).
 */

// ── Server-side only (route handlers) ──────────────────────

/** Project root (parent of frontend/, where CWD is frontend/) */
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

/** Python backend base URL (used by API route handlers to proxy requests) */
export const BACKEND_URL: string =
  process.env.BACKEND_URL || "http://localhost:8000";

/** Music directory for local track scanning (server-side fs access) */
const _rawMusicDir = process.env.MUSIC_DIR || "Documents/bili";
export const MUSIC_DIR: string = path.isAbsolute(_rawMusicDir)
  ? _rawMusicDir
  : path.join(PROJECT_ROOT, _rawMusicDir);

// ── Client-side safe (NEXT_PUBLIC_ prefix) ─────────────────

/** Base URL for client-side API calls (empty = same origin) */
export const CLIENT_API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL || "";

import { NextRequest } from "next/server";

export const maxDuration = 300;
export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();

  if (!body.message?.trim()) {
    return Response.json({ error: "message is required" }, { status: 400 });
  }

  const controller = new AbortController();
  // 10 minute timeout to support long-running agent operations (e.g. convert_video)
  const timeout = setTimeout(() => controller.abort(), 600_000);

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) {
      const text = await res.text();
      return Response.json(
        { error: `Backend error: ${res.status} ${text}` },
        { status: res.status }
      );
    }

    // Stream the backend SSE response directly to the client
    return new Response(res.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return Response.json({ error: "Request timed out" }, { status: 504 });
    }
    return Response.json({ error: String(err) }, { status: 502 });
  } finally {
    clearTimeout(timeout);
  }
}

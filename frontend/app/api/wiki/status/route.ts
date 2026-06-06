import { BACKEND_URL } from "@/app/lib/config";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/wiki/status`);
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return Response.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

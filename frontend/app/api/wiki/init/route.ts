import { BACKEND_URL } from "@/app/lib/config";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/wiki/init`, {
      method: "POST",
    });
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return Response.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

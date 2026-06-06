import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/app/lib/config";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.get("q") || "";
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/wiki/query?q=${encodeURIComponent(query)}`
    );
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return Response.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

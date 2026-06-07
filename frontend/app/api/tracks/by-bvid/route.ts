import { BACKEND_URL } from "@/app/lib/config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const bvid = searchParams.get("bvid");
  if (!bvid) {
    return Response.json({ detail: "bvid required" }, { status: 400 });
  }
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/tracks/by-bvid?bvid=${encodeURIComponent(bvid)}`
    );
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return Response.json({ detail: "Backend unavailable" }, { status: 502 });
  }
}

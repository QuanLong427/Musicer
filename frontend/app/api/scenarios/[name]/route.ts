import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/app/lib/config";

export const dynamic = "force-dynamic";

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/scenarios/${encodeURIComponent(name)}`,
      { method: "DELETE" }
    );
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return Response.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

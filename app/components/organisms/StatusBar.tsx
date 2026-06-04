"use client";

import { GlowDot } from "@/app/components/atoms/GlowDot";
import { Label } from "@/app/components/atoms/Label";
import { WikiStatus } from "@/app/components/molecules/WikiStatus";

export function StatusBar() {
  return (
    <footer
      className="flex shrink-0 flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-[var(--glass-border)] px-4 py-2 md:px-6"
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.03)",
      }}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="inline-flex items-center gap-2">
          <GlowDot color="primary" size={7} />
          <Label size="sm" className="text-[color:var(--color-cta)]">
            ONLINE
          </Label>
        </span>
        <Label size="sm">v1.0.4</Label>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1">
        <WikiStatus />
        <Label size="sm">SYNCED</Label>
      </div>
    </footer>
  );
}

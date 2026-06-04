"use client";

import { useEffect, useState } from "react";

/** Blinking cursor for the chat input */
export function BlockCursor() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const id = window.setInterval(() => {
      setVisible((v) => !v);
    }, 530);
    return () => window.clearInterval(id);
  }, []);

  return (
    <span
      className="inline-block h-[1em] min-h-[14px] w-[0.5em] align-middle rounded-full bg-[#818cf8]"
      style={{ opacity: visible ? 1 : 0 }}
      aria-hidden
    />
  );
}

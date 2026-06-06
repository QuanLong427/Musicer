"use client";

import { useState } from "react";
import { useAgent } from "@/app/context/AgentContext";

interface ScenarioSelectProps {
  value: string;
  onChange: (scenario: string) => void;
}

export function ScenarioSelect({ value, onChange }: ScenarioSelectProps) {
  const { scenarios, addScenario, deleteScenario } = useAgent();
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    await addScenario(newName.trim());
    onChange(newName.trim());
    setNewName("");
    setIsAdding(false);
  };

  const handleDelete = async (name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteScenario(name);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider transition-all duration-200 hover:bg-[rgba(129,140,248,0.15)]"
        style={{
          borderColor: "rgba(129,140,248,0.3)",
          color: "var(--color-primary)",
        }}
      >
        <span className="opacity-60">场景:</span>
        <span>{value}</span>
        <span className="opacity-40">{isOpen ? "▴" : "▾"}</span>
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 z-50 mt-1 min-w-[140px] rounded-lg border py-1"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "var(--glass-border)",
          }}
        >
          {scenarios.map((s) => (
            <div
              key={s}
              className="group flex items-center gap-1"
            >
              <button
                type="button"
                onClick={() => {
                  onChange(s);
                  setIsOpen(false);
                }}
                className="flex-1 px-3 py-1.5 text-left text-[11px] transition-colors hover:bg-[rgba(129,140,248,0.1)]"
                style={{
                  color: s === value ? "var(--color-primary)" : "var(--color-on-surface)",
                }}
              >
                {s}
              </button>
              {s !== "默认" && (
                <button
                  type="button"
                  onClick={(e) => handleDelete(s, e)}
                  className="mr-2 text-[10px] opacity-0 transition-opacity group-hover:opacity-60 hover:!opacity-100"
                  style={{ color: "var(--color-error, #fb7185)" }}
                  title={`删除场景「${s}」`}
                >
                  ×
                </button>
              )}
            </div>
          ))}

          <div className="border-t px-2 py-1" style={{ borderColor: "var(--glass-border)" }}>
            {isAdding ? (
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                  placeholder="场景名称"
                  className="flex-1 rounded border px-1.5 py-0.5 text-[11px]"
                  style={{
                    backgroundColor: "transparent",
                    borderColor: "var(--glass-border)",
                    color: "var(--color-on-surface)",
                  }}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={handleAdd}
                  className="text-[10px] font-medium"
                  style={{ color: "var(--color-primary)" }}
                >
                  添加
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsAdding(true)}
                className="w-full text-left text-[11px] opacity-60 transition-opacity hover:opacity-100"
                style={{ color: "var(--color-on-surface-muted)" }}
              >
                + 添加场景
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

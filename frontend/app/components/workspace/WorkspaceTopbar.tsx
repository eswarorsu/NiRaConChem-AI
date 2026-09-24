"use client";

import { ClockCounterClockwise, Robot } from "@phosphor-icons/react";

export type WorkspaceView = "chat" | "market" | "reports" | "profile";

const VIEWS: { key: WorkspaceView; label: string }[] = [
  { key: "chat", label: "AI Chat" },
  { key: "market", label: "Market" },
  { key: "reports", label: "Reports" },
  { key: "profile", label: "Session" },
];

type WorkspaceTopbarProps = {
  view: WorkspaceView | "subscription";
  onViewChange: (view: WorkspaceView) => void;
  questionCount: number;
  onToggleHistory: () => void;
  historyOpen: boolean;
};

export default function WorkspaceTopbar({
  view,
  onViewChange,
  questionCount,
  onToggleHistory,
  historyOpen,
}: WorkspaceTopbarProps) {
  return (
    <header className="ws-topbar">
      <nav aria-label="Views" className="ws-views">
        {VIEWS.map((item) => (
          <button
            aria-current={view === item.key ? "page" : undefined}
            className="ws-view"
            key={item.key}
            onClick={() => onViewChange(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="ws-utility">
        <button
          aria-expanded={historyOpen}
          aria-label="History"
          className="ws-icon-btn ws-history-toggle"
          onClick={onToggleHistory}
          type="button"
        >
          <ClockCounterClockwise aria-hidden="true" size={19} weight="duotone" />
        </button>
        <span className="ws-status">
          <span aria-hidden="true" className="ws-status-dot" />
          {questionCount === 0
            ? "New session"
            : `${questionCount} question${questionCount > 1 ? "s" : ""} this session`}
        </span>
        <span aria-hidden="true" className="ws-avatar">
          <Robot size={20} weight="duotone" />
        </span>
      </div>
    </header>
  );
}

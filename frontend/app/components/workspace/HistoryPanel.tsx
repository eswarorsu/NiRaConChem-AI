"use client";

import { ChatsCircle, Plus, X } from "@phosphor-icons/react";

import { groupByDay, type SavedConversation } from "../../hooks/useChatHistory";

type HistoryPanelProps = {
  items: SavedConversation[];
  activeId: string | null;
  onOpen: (id: string) => void;
  onNewChat: () => void;
  onClear: () => void;
  /** Narrow screens show the panel as a drawer with its own close button. */
  onClose?: () => void;
};

export default function HistoryPanel({ items, activeId, onOpen, onNewChat, onClear, onClose }: HistoryPanelProps) {
  const groups = groupByDay(items);

  return (
    <aside aria-labelledby="ws-history-title" className="ws-history">
      <header className="ws-history-head">
        <h2 id="ws-history-title">History</h2>
        <button className="ws-pill-btn" onClick={onNewChat} type="button">
          <Plus aria-hidden="true" size={16} weight="bold" />
          New chat
        </button>
        {onClose ? (
          <button aria-label="Close history" className="ws-icon-btn ws-history-close" onClick={onClose} type="button">
            <X aria-hidden="true" size={18} weight="bold" />
          </button>
        ) : null}
      </header>

      <div className="ws-history-scroll">
        {groups.length === 0 ? (
          <p className="ws-history-empty">
            Your questions will collect here. They stay in this browser — nothing is stored on a server.
          </p>
        ) : (
          groups.map((group) => (
            <section className="ws-history-group" key={group.label}>
              <h3>{group.label}</h3>
              <ul>
                {group.items.map((item) => (
                  <li key={item.id}>
                    <button
                      aria-current={item.id === activeId ? "true" : undefined}
                      className="ws-history-row"
                      onClick={() => onOpen(item.id)}
                      title={item.title}
                      type="button"
                    >
                      <span aria-hidden="true" className="ws-history-icon">
                        <ChatsCircle size={17} weight="duotone" />
                      </span>
                      <span className="ws-history-text">{item.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </div>

      {groups.length ? (
        <button className="ws-history-clear" onClick={onClear} type="button">
          Clear history on this device
        </button>
      ) : null}
    </aside>
  );
}

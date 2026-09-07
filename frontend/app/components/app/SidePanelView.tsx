"use client";

import { FileText } from "@phosphor-icons/react";

import { API_BASE_URL } from "../../lib/api";
import type { ChatMessage, SidePanel } from "../../lib/types";

type SidePanelViewProps = {
  panel: Exclude<SidePanel, "chat">;
  messages: ChatMessage[];
  sessionActive: boolean;
};

/**
 * The non-conversation views. Everything shown here is derived from the live
 * session — there is no account system behind this product yet, so inventing a
 * profile with a name, a company and a phone number would have been a lie told
 * in the UI.
 */
export default function SidePanelView({ panel, messages, sessionActive }: SidePanelViewProps) {
  if (panel === "reports") {
    const reports = messages.filter((m) => m.role === "assistant" && m.report_ready);
    return (
      <div className="side-panel-view">
        <h2 className="side-panel-title">Reports history</h2>
        {reports.length === 0 ? (
          <p className="side-panel-empty">
            No reports yet. Ask a project question — once the backend has enough detail it will
            offer a technical PDF.
          </p>
        ) : (
          <ul className="side-panel-list">
            {reports.map((message, index) => (
              <li className="side-panel-list-item" key={index}>
                <FileText size={16} aria-hidden="true" weight="duotone" />
                <span>
                  {message.content.slice(0, 90)}
                  {message.content.length > 90 ? "…" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="side-panel-note">
          Reports live in this session only. They are generated on demand and not stored.
        </p>
      </div>
    );
  }

  if (panel === "subscription") {
    return (
      <div className="side-panel-view">
        <h2 className="side-panel-title">Subscription</h2>
        <p className="side-panel-empty">
          Billing is not configured for this deployment. Every capability is currently available
          without a plan.
        </p>
      </div>
    );
  }

  return (
    <div className="side-panel-view">
      <h2 className="side-panel-title">Session</h2>
      <p className="side-panel-empty">
        No account system is connected, so nothing here is tied to a person — this is what the
        current browser session holds.
      </p>
      <div className="profile-grid">
        <div className="info-row">
          <span>Conversation</span>
          <strong>{sessionActive ? "Active" : "Not started"}</strong>
        </div>
        <div className="info-row">
          <span>Messages sent</span>
          <strong>{messages.filter((m) => m.role === "user").length}</strong>
        </div>
        <div className="info-row">
          <span>Reports generated</span>
          <strong>{messages.filter((m) => m.role === "assistant" && m.report_ready).length}</strong>
        </div>
        <div className="info-row">
          <span>Recommendation service</span>
          <strong>{API_BASE_URL}</strong>
        </div>
      </div>
    </div>
  );
}

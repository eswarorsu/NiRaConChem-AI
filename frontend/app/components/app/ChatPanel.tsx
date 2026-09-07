"use client";

import { Sparkle, UserCircle } from "@phosphor-icons/react";

import AnswerCard from "../AnswerCard";
import { renderAssistantContent } from "../../lib/chat-format";
import type { ChatMessage } from "../../lib/types";

type ChatPanelProps = {
  messages: ChatMessage[];
  isAssistantTyping: boolean;
  canDownloadReport: boolean;
  isDownloading: boolean;
  onDownloadReport: () => void;
};

export default function ChatPanel({
  messages,
  isAssistantTyping,
  canDownloadReport,
  isDownloading,
  onDownloadReport,
}: ChatPanelProps) {
  const awaitingFirstToken = isAssistantTyping && messages.at(-1)?.role === "user";

  return (
    <>
      <div className="chat-messages">
        {messages.map((message, index) => {
          if (message.role === "user") {
            return (
              <div className="chat-message user" key={`user-${index}`}>
                <span className="chat-avatar" aria-hidden="true">
                  <UserCircle size={15} weight="duotone" />
                </span>
                <p>{message.content}</p>
              </div>
            );
          }

          // The structured card replaces the markdown once the typing animation
          // has caught up; mid-animation the text still reads as being written.
          const stillTyping =
            message.visibleContent !== undefined &&
            message.visibleContent.length < message.content.length;

          return (
            <div className="chat-message assistant" key={`assistant-${index}`}>
              <span className="chat-avatar" aria-hidden="true">
                <Sparkle size={15} weight="duotone" />
              </span>
              {message.structured && !stillTyping ? (
                <AnswerCard answer={message.structured} />
              ) : (
                renderAssistantContent(message.visibleContent ?? message.content, stillTyping)
              )}
            </div>
          );
        })}

        {awaitingFirstToken ? (
          <div className="chat-message assistant typing-preview">
            <span className="chat-avatar" aria-hidden="true">
              <Sparkle size={15} weight="duotone" />
            </span>
            <p aria-label="NiRaConChem AI is typing">
              <span />
              <span />
              <span />
            </p>
          </div>
        ) : null}
      </div>

      {canDownloadReport ? (
        <button
          className="download-button"
          disabled={isDownloading}
          onClick={onDownloadReport}
          type="button"
        >
          {isDownloading ? "Preparing PDF" : "Download PDF report"}
        </button>
      ) : null}
    </>
  );
}

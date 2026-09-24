"use client";

import {
  Buildings,
  Drop,
  HouseLine,
  Paperclip,
  PaperPlaneRight,
  Sparkle,
  Wrench,
} from "@phosphor-icons/react";
import { useEffect, type ChangeEvent, type FormEvent, type KeyboardEvent, type RefObject } from "react";

/** Starters fill the box rather than sending, so the user can add their own detail. */
const STARTERS = [
  {
    label: "Exposed roof",
    icon: HouseLine,
    text: "Exposed concrete roof in Dubai, surface reaches 70 °C in summer — which waterproofing system?",
  },
  {
    label: "Basement",
    icon: Buildings,
    text: "Basement below the water table with hydrostatic pressure from outside — waterproofing options?",
  },
  {
    label: "Wet room",
    icon: Drop,
    text: "Shower and bathroom floors over a concrete slab — waterproofing under the tiles?",
  },
  {
    label: "Concrete repair",
    icon: Wrench,
    text: "Spalled concrete column near the coast with exposed rebar — which repair system?",
  },
];

type ComposerProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  isLoading: boolean;
  isAssistantTyping: boolean;
  isAnalyzingFile: boolean;
};

/**
 * The workspace's message box. Same state as the landing search (query, file,
 * submit all live in useChatSession) in a taller, calmer form: a writing area,
 * starters underneath, attach on the left and send on the right.
 */
export default function Composer({
  query,
  onQueryChange,
  onSubmit,
  onFileUpload,
  inputRef,
  isLoading,
  isAssistantTyping,
  isAnalyzingFile,
}: ComposerProps) {
  // Grow with the text up to a comfortable height.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [query, inputRef]);

  const busy = isLoading || isAssistantTyping;

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (!busy && query.trim()) event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form aria-label="Ask NiRaConChem AI" className="ws-composer" onSubmit={onSubmit}>
      <div className="ws-composer-field">
        <Sparkle aria-hidden="true" className="ws-composer-spark" size={18} weight="fill" />
        <label className="sr-only" htmlFor="ws-query">
          Describe a project condition
        </label>
        <textarea
          id="ws-query"
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Describe the substrate, the exposure and what has to stop — NiRa reads the datasheets."
          ref={inputRef}
          rows={2}
          value={query}
        />
      </div>

      <div className="ws-composer-bar">
        <label className="ws-icon-btn" htmlFor="ws-file" title="Attach a project file (PDF, DOCX, XLSX, TXT)">
          <Paperclip aria-hidden="true" size={18} weight="bold" />
          <span className="sr-only">Attach a project file</span>
        </label>
        <input
          accept=".pdf,.docx,.xlsx,.txt"
          className="sr-only"
          disabled={isAnalyzingFile}
          id="ws-file"
          onChange={onFileUpload}
          type="file"
        />

        <div aria-label="Starters" className="ws-starters" role="group">
          {STARTERS.map(({ label, icon: Icon, text }) => (
            <button
              className="ws-chip"
              key={label}
              onClick={() => {
                onQueryChange(text);
                inputRef.current?.focus();
              }}
              type="button"
            >
              <Icon aria-hidden="true" size={16} weight="duotone" />
              {label}
            </button>
          ))}
        </div>

        {isAnalyzingFile ? <span className="ws-composer-status">Reading the file…</span> : null}

        <button
          aria-label={isLoading ? "Thinking" : "Send"}
          className="ws-send"
          disabled={busy || !query.trim()}
          type="submit"
        >
          <PaperPlaneRight aria-hidden="true" size={20} weight="fill" />
        </button>
      </div>
    </form>
  );
}

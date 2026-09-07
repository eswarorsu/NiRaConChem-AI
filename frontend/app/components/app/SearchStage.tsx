"use client";

import { PaperPlaneTilt, Paperclip } from "@phosphor-icons/react";
import type { ChangeEvent, FormEvent, RefObject } from "react";

const EXAMPLES: string[] = [];

type SearchStageProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onExample: (value: string) => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  inputRef: RefObject<HTMLInputElement | null>;
  hasChatStarted: boolean;
  isLoading: boolean;
  isAssistantTyping: boolean;
  isAnalyzingFile: boolean;
};

/**
 * The one live search form. It is rendered inside the landing hero before a
 * conversation starts and on its own afterwards — same element, same state, so
 * nothing remounts at the moment the product takes over.
 */
export default function SearchStage({
  query,
  onQueryChange,
  onSubmit,
  onExample,
  onFileUpload,
  inputRef,
  hasChatStarted,
  isLoading,
  isAssistantTyping,
  isAnalyzingFile,
}: SearchStageProps) {
  return (
    <section
      aria-label="Construction chemicals search"
      className={`search-stage${hasChatStarted ? " has-result" : ""}`}
    >
      <form className="search-box" onSubmit={onSubmit}>
        <label className="upload-icon-button" htmlFor="project-file" title="Upload project file">
          <Paperclip size={20} aria-hidden="true" weight="bold" />
          <span className="sr-only">Upload project file</span>
        </label>
        <input
          accept=".pdf,.docx,.xlsx,.txt"
          disabled={isAnalyzingFile}
          id="project-file"
          onChange={onFileUpload}
          type="file"
        />
        <input
          aria-label="Construction chemical recommendation query"
          className="query-input"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Describe a project condition — waterproofing a Dubai basement, hydrostatic pressure…"
          ref={inputRef}
          type="search"
          value={query}
        />
        <button disabled={isLoading || isAssistantTyping} type="submit">
          <span>{isLoading ? "Thinking" : "Send"}</span>
          <PaperPlaneTilt size={17} aria-hidden="true" weight="bold" />
        </button>
      </form>

      {!hasChatStarted && EXAMPLES.length ? (
        <div className="quick-prompts" aria-label="Example searches">
          {EXAMPLES.map((example) => (
            <button key={example} onClick={() => onExample(example)} type="button">
              {example}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

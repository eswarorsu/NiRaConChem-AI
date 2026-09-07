"use client";

import { useRef, type FormEvent } from "react";
import { DownloadSimple } from "@phosphor-icons/react";

import AppSidebar from "./components/app/AppSidebar";
import ChatPanel from "./components/app/ChatPanel";
import FileSummary from "./components/app/FileSummary";
import MarketResults from "./components/app/MarketResults";
import SearchStage from "./components/app/SearchStage";
import SidePanelView from "./components/app/SidePanelView";
import ThemeToggle from "./components/app/ThemeToggle";
import LandingPage from "./components/landing/LandingPage";
import { scrollToId } from "./components/landing/nav";
import { useChatSession } from "./hooks/useChatSession";
import { useInstallPrompt } from "./hooks/useInstallPrompt";
import { setTheme, useApplyTheme, useTheme } from "./lib/theme";

/**
 * One route, two surfaces.
 *
 * Before a conversation starts the page is the landing experience; the moment a
 * query is sent it becomes the workspace. The search form is handed to the
 * landing hero rather than duplicated, so it never remounts across that switch.
 *
 * This component composes — it holds no transport, no transcript and no timers.
 * All of that lives in useChatSession.
 */
export default function Home() {
  const session = useChatSession();
  const { canInstall, install } = useInstallPrompt();
  const isDark = useTheme() === "dark";
  useApplyTheme(isDark);
  const queryInputRef = useRef<HTMLInputElement>(null);

  const {
    activeMode,
    chatMessages,
    error,
    fileAnalysis,
    hasChatStarted,
    isProjectQuery,
    latestChat,
    marketProducts,
    sidePanel,
  } = session;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void session.submitChat(session.query);
  }

  function handleExample(example: string) {
    void session.submitChat(example);
  }

  /** Landing CTAs return the visitor to the live search field rather than to an
   *  invented route — there is only one page. */
  function handleTryAi() {
    scrollToId("top");
    window.setTimeout(() => queryInputRef.current?.focus(), 420);
  }

  const searchStage = (
    <SearchStage
      hasChatStarted={hasChatStarted}
      inputRef={queryInputRef}
      isAnalyzingFile={session.isAnalyzingFile}
      isAssistantTyping={session.isAssistantTyping}
      isLoading={session.isLoading}
      onExample={handleExample}
      onFileUpload={session.handleFileUpload}
      onQueryChange={session.setQuery}
      onSubmit={handleSubmit}
      query={session.query}
    />
  );

  if (!hasChatStarted) {
    return (
      <main className={`home is-landing${isDark ? " dark-theme" : ""}`}>
        <LandingPage
          canInstall={canInstall}
          onInstall={install}
          onTryAi={handleTryAi}
          searchSlot={searchStage}
        />
      </main>
    );
  }

  return (
    <main className={`home has-result${isDark ? " dark-theme" : ""}`}>
      <ThemeToggle isDark={isDark} onToggle={() => setTheme(isDark ? "light" : "dark")} />

      {canInstall ? (
        <button className="app-install-button" onClick={install} title="Install app" type="button">
          <span className="install-text">Install</span>
          <span className="install-icon" aria-hidden="true">
            <DownloadSimple size={18} weight="bold" />
          </span>
        </button>
      ) : null}

      <AppSidebar
        activeMode={activeMode}
        onClearChat={session.resetSession}
        onModeChange={(mode) => {
          session.setActiveMode(mode);
          session.setSidePanel("chat");
        }}
        onPanelChange={session.setSidePanel}
        sidePanel={sidePanel}
      />

      {searchStage}

      {fileAnalysis ? (
        <FileSummary fileAnalysis={fileAnalysis} onClear={session.clearFileAnalysis} />
      ) : null}

      {error ? (
        <p className="error-text" role="alert">
          {error}
        </p>
      ) : null}

      <section className="chat-panel" aria-label="NiRaConChem AI workspace">
        {sidePanel !== "chat" ? (
          <SidePanelView messages={chatMessages} panel={sidePanel} sessionActive={hasChatStarted} />
        ) : (
          <>
            <div className="chat-header">
              <span>{activeMode === "market" ? "Market results" : "NiRaConChem AI"}</span>
              {activeMode === "market" ? (
                <strong>{marketProducts.length} matches</strong>
              ) : isProjectQuery ? (
                <strong>{latestChat?.report_ready ? "Report ready" : "Collecting project data"}</strong>
              ) : (
                <strong>General answer</strong>
              )}
            </div>

            {activeMode === "market" ? (
              <MarketResults isProjectQuery={isProjectQuery} products={marketProducts} />
            ) : (
              <ChatPanel
                canDownloadReport={Boolean(latestChat?.report_ready) && isProjectQuery}
                isAssistantTyping={session.isAssistantTyping}
                isDownloading={session.isDownloading}
                messages={chatMessages}
                onDownloadReport={session.downloadReport}
              />
            )}
          </>
        )}
      </section>
    </main>
  );
}

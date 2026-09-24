"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import ChatPanel from "./components/app/ChatPanel";
import FileSummary from "./components/app/FileSummary";
import MarketResults from "./components/app/MarketResults";
import SearchStage from "./components/app/SearchStage";
import SidePanelView from "./components/app/SidePanelView";
import LandingPage from "./components/landing/LandingPage";
import { scrollToId } from "./components/landing/nav";
import ChatCard from "./components/workspace/ChatCard";
import Composer from "./components/workspace/Composer";
import Greeting from "./components/workspace/Greeting";
import HistoryPanel from "./components/workspace/HistoryPanel";
import WorkspaceRail from "./components/workspace/WorkspaceRail";
import WorkspaceTopbar, { type WorkspaceView } from "./components/workspace/WorkspaceTopbar";
import { useChatHistory } from "./hooks/useChatHistory";
import { useChatSession } from "./hooks/useChatSession";
import { useInstallPrompt } from "./hooks/useInstallPrompt";
import { useApplyTheme, useTheme } from "./lib/theme";

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
  const composerRef = useRef<HTMLTextAreaElement>(null);
  // "New chat" keeps the workspace open on its empty state; only "Back to the
  // home page" returns to the landing surface.
  const [stayInWorkspace, setStayInWorkspace] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

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

  const history = useChatHistory({
    messages: chatMessages,
    sessionId: session.sessionId,
    isAssistantTyping: session.isAssistantTyping,
  });

  const showWorkspace = hasChatStarted || stayInWorkspace;

  // Focus the message box whenever the empty workspace opens.
  useEffect(() => {
    if (showWorkspace && !hasChatStarted) composerRef.current?.focus();
  }, [showWorkspace, hasChatStarted]);

  function startNewChat() {
    session.resetSession();
    session.setActiveMode("nira");
    history.startNew();
    setStayInWorkspace(true);
    setHistoryOpen(false);
  }

  function goHome() {
    session.resetSession();
    history.startNew();
    setStayInWorkspace(false);
    setHistoryOpen(false);
    window.scrollTo({ top: 0 });
  }

  function openConversation(id: string) {
    const saved = history.select(id);
    if (!saved) return;
    session.loadConversation({ messages: saved.messages, sessionId: saved.sessionId });
    setStayInWorkspace(true);
    setHistoryOpen(false);
  }

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

  if (!showWorkspace) {
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

  const view: WorkspaceView | "subscription" =
    sidePanel === "reports"
      ? "reports"
      : sidePanel === "profile"
        ? "profile"
        : sidePanel === "subscription"
          ? "subscription"
          : activeMode === "market"
            ? "market"
            : "chat";

  function changeView(next: WorkspaceView) {
    if (next === "chat" || next === "market") {
      session.setActiveMode(next === "market" ? "market" : "nira");
      session.setSidePanel("chat");
    } else {
      session.setSidePanel(next);
    }
  }

  const canDownloadReport = Boolean(latestChat?.report_ready) && isProjectQuery;

  const cardTitle = {
    chat: "NiRa AI",
    market: "Market results",
    reports: "Reports",
    profile: "Session",
    subscription: "Subscription",
  }[view];

  const cardStatus =
    view === "market"
      ? `${marketProducts.length} matches`
      : view === "chat" && hasChatStarted
        ? isProjectQuery
          ? latestChat?.report_ready
            ? "Report ready"
            : "Collecting project data"
          : "General answer"
        : null;

  const questionCount = chatMessages.filter((message) => message.role === "user").length;

  const historyPanel = (
    <HistoryPanel
      activeId={history.activeId}
      items={history.items}
      onClear={history.clear}
      onClose={historyOpen ? () => setHistoryOpen(false) : undefined}
      onNewChat={startNewChat}
      onOpen={openConversation}
    />
  );

  return (
    <main className={`home has-result ws${isDark ? " dark-theme" : ""}`}>
      <h1 className="sr-only">NiRaConChem AI workspace</h1>
      <div className="ws-backdrop" aria-hidden="true" />
      <div className="ws-frame">
        <WorkspaceRail
          canDownloadReport={canDownloadReport}
          canInstall={canInstall}
          isDownloading={session.isDownloading}
          onDownloadReport={session.downloadReport}
          onHome={goHome}
          onInstall={install}
          onNewChat={startNewChat}
          onSubscription={() => session.setSidePanel("subscription")}
          subscriptionActive={view === "subscription"}
        />

        <WorkspaceTopbar
          historyOpen={historyOpen}
          onToggleHistory={() => setHistoryOpen((open) => !open)}
          onViewChange={changeView}
          questionCount={questionCount}
          view={view}
        />

        <ChatCard
          canDownloadReport={canDownloadReport}
          centered={view === "chat" && !hasChatStarted}
          footer={
            view === "chat" || view === "market" ? (
              <>
                {fileAnalysis ? (
                  <FileSummary fileAnalysis={fileAnalysis} onClear={session.clearFileAnalysis} />
                ) : null}
                {error ? (
                  <p className="ws-error" role="alert">
                    {error}
                  </p>
                ) : null}
                <Composer
                  inputRef={composerRef}
                  isAnalyzingFile={session.isAnalyzingFile}
                  isAssistantTyping={session.isAssistantTyping}
                  isLoading={session.isLoading}
                  onFileUpload={session.handleFileUpload}
                  onQueryChange={session.setQuery}
                  onSubmit={handleSubmit}
                  query={session.query}
                />
              </>
            ) : null
          }
          isDownloading={session.isDownloading}
          onDownloadReport={session.downloadReport}
          onHome={goHome}
          onNewChat={startNewChat}
          status={cardStatus}
          title={cardTitle}
        >
          {view === "reports" || view === "profile" || view === "subscription" ? (
            <SidePanelView messages={chatMessages} panel={view} sessionActive={hasChatStarted} />
          ) : view === "market" ? (
            <MarketResults isProjectQuery={isProjectQuery} products={marketProducts} />
          ) : hasChatStarted ? (
            <ChatPanel
              canDownloadReport={canDownloadReport}
              isAssistantTyping={session.isAssistantTyping}
              isDownloading={session.isDownloading}
              messages={chatMessages}
              onDownloadReport={session.downloadReport}
            />
          ) : (
            <Greeting />
          )}
        </ChatCard>

        <div className="ws-history-dock">{historyPanel}</div>
      </div>

      {historyOpen ? (
        <div className="ws-drawer" role="dialog" aria-modal="true" aria-label="History">
          <button
            aria-label="Close history"
            className="ws-drawer-scrim"
            onClick={() => setHistoryOpen(false)}
            tabIndex={-1}
            type="button"
          />
          {historyPanel}
        </div>
      ) : null}
    </main>
  );
}

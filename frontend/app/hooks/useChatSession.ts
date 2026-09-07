"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import type { StructuredAnswer } from "../components/AnswerCard";
import { postChat, postFileAnalysis, postReport } from "../lib/api";
import { isConstructionRelatedQuery, normalizeChatReply } from "../lib/chat-format";
import { marketSearchText, selectMarketProducts } from "../lib/market";
import type {
  ActiveMode,
  ChatMessage,
  ChatResponse,
  FileAnalysis,
  SidePanel,
} from "../lib/types";

const TYPING_INTERVAL_MS = 18;
const TYPING_CHARS_PER_TICK = 3;

function describeFailure(error: unknown, timeout: string, generic: string) {
  if (error instanceof DOMException && error.name === "AbortError") return timeout;
  const detail = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  return `${generic} ${detail}`;
}

/**
 * The whole conversation: transport, transcript, typing animation, uploaded
 * project document, PDF export and which panel is on screen.
 *
 * This used to be 34 hooks and sixteen handlers inline in the page component,
 * which meant every view change risked the transport and vice versa. The page
 * now only composes views; nothing here touches the DOM except the PDF download.
 */
export function useChatSession() {
  const [query, setQuery] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [latestChat, setLatestChat] = useState<ChatResponse | null>(null);
  const [reportPayload, setReportPayload] = useState<ChatResponse["report_payload"]>(null);
  const [fileAnalysis, setFileAnalysis] = useState<FileAnalysis | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzingFile, setIsAnalyzingFile] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [isProjectQuery, setIsProjectQuery] = useState(false);
  const [error, setError] = useState("");

  const [activeMode, setActiveMode] = useState<ActiveMode>("nira");
  const [sidePanel, setSidePanel] = useState<SidePanel>("chat");

  const typingIntervalRef = useRef<number | null>(null);

  const hasChatStarted = chatMessages.some((message) => message.role === "user");

  const latestUserMessage =
    [...chatMessages].reverse().find((message) => message.role === "user")?.content || query;

  const marketProducts = useMemo(
    () => selectMarketProducts(marketSearchText(latestUserMessage, latestChat)),
    [latestUserMessage, latestChat],
  );

  const reportCount = chatMessages.filter((m) => m.role === "assistant" && m.report_ready).length;

  const clearTypingAnimation = useCallback(() => {
    if (typingIntervalRef.current) {
      window.clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
  }, []);

  useEffect(() => clearTypingAnimation, [clearTypingAnimation]);

  /** Reveals the reply a few characters at a time, so it reads as written
   *  rather than pasted. The structured card replaces the text once caught up. */
  const animateAssistantMessage = useCallback(
    (content: string, structured?: StructuredAnswer | null) => {
      clearTypingAnimation();
      setIsAssistantTyping(true);
      setChatMessages((current) => [
        ...current,
        { role: "assistant", content, visibleContent: "", structured: structured ?? null },
      ]);

      let index = 0;
      typingIntervalRef.current = window.setInterval(() => {
        index += TYPING_CHARS_PER_TICK;
        const nextContent = content.slice(0, index);
        setChatMessages((current) => {
          const next = [...current];
          const lastIndex = next.length - 1;
          if (lastIndex < 0 || next[lastIndex].role !== "assistant") return current;
          next[lastIndex] = { ...next[lastIndex], visibleContent: nextContent };
          return next;
        });

        if (index >= content.length) {
          clearTypingAnimation();
          setIsAssistantTyping(false);
        }
      }, TYPING_INTERVAL_MS);
    },
    [clearTypingAnimation],
  );

  const submitChat = useCallback(
    async (nextMessage: string) => {
      const trimmedMessage = nextMessage.trim();
      if (!trimmedMessage) {
        setError("Enter a construction chemical requirement first.");
        return;
      }

      setIsLoading(true);
      setIsAssistantTyping(true);
      setError("");
      setActiveMode("nira");
      setIsProjectQuery(isConstructionRelatedQuery(trimmedMessage) || Boolean(fileAnalysis));
      setChatMessages((current) => [...current, { role: "user", content: trimmedMessage }]);
      setQuery("");

      try {
        const data = await postChat({
          message: trimmedMessage,
          session_id: sessionId,
          document_context: fileAnalysis?.preview,
          document_name: fileAnalysis?.filename,
        });

        const normalized = { ...data, reply: normalizeChatReply(data.reply, trimmedMessage) };
        setSessionId(normalized.session_id);
        setLatestChat(normalized);
        setReportPayload(normalized.report_payload || null);
        animateAssistantMessage(normalized.reply, normalized.structured);

        if (normalized.report_ready) {
          setChatMessages((current) => {
            const next = [...current];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0 && next[lastIndex].role === "assistant") {
              next[lastIndex] = { ...next[lastIndex], report_ready: true };
            }
            return next;
          });
        }

        if (normalized.intent === "technical_consultation" && !normalized.needs_clarification) {
          setActiveMode("market");
        }
        if (normalized.report_ready && normalized.report_payload?.query?.trim()) {
          setQuery("");
        }
      } catch (caught) {
        setError(
          describeFailure(
            caught,
            "NiRaConChem AI took too long to respond. The backend may be waking up.",
            "Chat backend not reachable.",
          ),
        );
        clearTypingAnimation();
        setIsAssistantTyping(false);
        // Keep the user's message so the view stays in the conversation rather
        // than snapping back to the landing page.
        setChatMessages((current) => [
          ...current,
          {
            role: "assistant",
            content:
              "I couldn't reach the recommendation service just now. Your message was kept — please try again in a moment.",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [animateAssistantMessage, clearTypingAnimation, fileAnalysis, sessionId],
  );

  const handleFileUpload = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsAnalyzingFile(true);
    setError("");
    try {
      setFileAnalysis(await postFileAnalysis(file));
    } catch (caught) {
      setError(
        describeFailure(
          caught,
          "File analysis took too long. Check that the backend is running.",
          "Could not read that file. Check the backend URL, CORS and file type.",
        ),
      );
      setFileAnalysis(null);
    } finally {
      setIsAnalyzingFile(false);
      event.target.value = "";
    }
  }, []);

  const downloadReport = useCallback(async () => {
    const trimmedQuery = reportPayload?.query?.trim() || query.trim();
    if (!trimmedQuery) {
      setError("Generate a recommendation before downloading a PDF.");
      return;
    }

    setIsDownloading(true);
    setError("");
    try {
      const blob = await postReport({
        query: trimmedQuery,
        document_context: reportPayload?.document_context || fileAnalysis?.preview,
        document_name: reportPayload?.document_name || fileAnalysis?.filename,
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "niraconchem-recommendation.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(
        describeFailure(
          caught,
          "PDF generation took too long. Check that the backend is running.",
          "Could not download the PDF report.",
        ),
      );
    } finally {
      setIsDownloading(false);
    }
  }, [fileAnalysis, query, reportPayload]);

  const resetSession = useCallback(() => {
    clearTypingAnimation();
    setChatMessages([]);
    setSessionId(null);
    setLatestChat(null);
    setReportPayload(null);
    setFileAnalysis(null);
    setQuery("");
    setError("");
    setSidePanel("chat");
    setIsAssistantTyping(false);
  }, [clearTypingAnimation]);

  return {
    // transcript
    chatMessages,
    latestChat,
    hasChatStarted,
    isProjectQuery,
    reportCount,
    // input
    query,
    setQuery,
    submitChat,
    // status
    isLoading,
    isAnalyzingFile,
    isDownloading,
    isAssistantTyping,
    error,
    setError,
    // document
    fileAnalysis,
    handleFileUpload,
    clearFileAnalysis: () => setFileAnalysis(null),
    // export
    downloadReport,
    // views
    activeMode,
    setActiveMode,
    sidePanel,
    setSidePanel,
    marketProducts,
    // lifecycle
    resetSession,
  };
}

"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { Moon, Paperclip, Sun, User } from "lucide-react";
import BlinkingEyes from "./components/BlinkingEyes";
import { ParticleWaveBackground } from "./components/ParticleWaveBackground";

const RENDER_API_BASE_URL = "https://niraconchem-ai.onrender.com";
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const API_BASE_URL =
  process.env.NODE_ENV === "development"
    ? configuredApiBaseUrl || "http://localhost:8000"
    : configuredApiBaseUrl?.includes("onrender.com")
      ? configuredApiBaseUrl
      : RENDER_API_BASE_URL;
const API_TIMEOUT_MS = 45000;

type Recommendation = {
  project_summary: string;
  detected_location: string;
  climate_context: string[];
  recommended_categories: string[];
  application_guidance: string[];
  missing_information: string[];
  ai_recommendation?: string | null;
  ai_precautions?: string[];
  ai_questions?: string[];
  source: string;
  document_name?: string | null;
  document_preview?: string | null;
  rag_sources: string[];
  rag_context: string[];
  best_recommended_system?: string | null;
  best_manufacturer?: string | null;
  recommended_products: Record<string, string>;
  why_recommended: string[];
  supporting_datasheet_references: string[];
  selected_product_profile?: {
    product_name?: string;
    system_type?: string;
    category?: string;
    application_areas?: string[];
    performance?: Record<string, string>;
    score?: number;
  } | null;
};

type FileAnalysis = {
  filename: string;
  file_type: string;
  extracted_characters: number;
  preview: string;
  locations: string[];
  construction_areas: string[];
  requirements: string[];
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  visibleContent?: string;
};

type ChatResponse = {
  session_id: string;
  reply: string;
  intent: string;
  needs_clarification: boolean;
  questions: string[];
  sources: string[];
  recommendation?: Record<string, unknown> | null;
  requirements: Record<string, string | null>;
  missing_requirements: string[];
  report_ready: boolean;
  report_endpoint?: string | null;
  report_payload?: {
    query?: string;
    document_context?: string;
    document_name?: string;
  } | null;
};

type ClarificationAnswers = {
  area: string;
  exposure: string;
  substrate: string;
  location: string;
  notes: string;
};

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

const examples = [
  "I need waterproofing",
  "Dubai basement concrete hydrostatic pressure",
  "Who founded NIRACONCHEM AI?",
];

const clarificationOptions = {
  area: ["Roof", "Basement", "Wet area", "Parking floor", "Concrete repair", "Expansion joint"],
  exposure: ["UV and heat", "Water pressure", "Coastal chloride", "Vehicle traffic", "Chemical exposure", "Interior use"],
  substrate: ["Concrete", "Screed", "Existing tiles", "Metal", "Blockwork", "Not sure"],
  location: ["Dubai", "Abu Dhabi", "Sharjah", "Coastal UAE", "UAE general"],
};

const broadTerms = ["waterproofing", "flooring", "repair", "coating", "sealant", "tile adhesive", "chemical"];
const areaTerms = ["roof", "rooftop", "basement", "bathroom", "wet", "parking", "floor", "joint", "tank", "pool", "wall", "slab", "villa"];
const exposureTerms = ["uv", "heat", "traffic", "chemical", "chloride", "coastal", "water", "pressure", "potable", "external", "interior", "crack"];
const substrateTerms = ["concrete", "screed", "tile", "metal", "block", "masonry", "plaster"];

function displayValue(value?: string | null) {
  return value && value.trim() ? value : "Not specified in retrieved datasheet";
}

function includesAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function shouldAskClarifyingQuestions(value: string, hasFileContext: boolean) {
  const normalized = value.toLowerCase().trim();
  const words = normalized.split(/\s+/).filter(Boolean);
  const isBroadCategory = broadTerms.some((term) => normalized === term || normalized === `${term} chemicals`);
  const missingArea = !includesAny(normalized, areaTerms);
  const missingExposure = !includesAny(normalized, exposureTerms);
  const missingSubstrate = !includesAny(normalized, substrateTerms);
  const missingCount = [missingArea, missingExposure, missingSubstrate].filter(Boolean).length;

  return !hasFileContext && (isBroadCategory || words.length <= 3 || missingCount >= 2);
}

async function apiFetch(path: string, options: RequestInit) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [latestChat, setLatestChat] = useState<ChatResponse | null>(null);
  const [reportPayload, setReportPayload] = useState<ChatResponse["report_payload"]>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [fileAnalysis, setFileAnalysis] = useState<FileAnalysis | null>(null);
  const [showClarifier, setShowClarifier] = useState(false);
  const [clarification, setClarification] = useState<ClarificationAnswers>({
    area: "",
    exposure: "",
    substrate: "",
    location: "",
    notes: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzingFile, setIsAnalyzingFile] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [error, setError] = useState("");
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const typingIntervalRef = useRef<number | null>(null);
  const hasChatStarted = chatMessages.some((message) => message.role === "user");

  useEffect(() => {
    setIsDarkTheme(localStorage.getItem("niraconchem-theme") === "dark");
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("theme-dark-body", isDarkTheme);
    document.body.classList.toggle("theme-dark-body", isDarkTheme);
  }, [isDarkTheme]);

  useEffect(() => {
    function handleBeforeInstallPrompt(event: Event) {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    }

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
  }, []);

  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) {
        window.clearInterval(typingIntervalRef.current);
      }
    };
  }, []);

  function clearTypingAnimation() {
    if (typingIntervalRef.current) {
      window.clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
  }

  function animateAssistantMessage(content: string) {
    clearTypingAnimation();
    setIsAssistantTyping(true);
    setChatMessages((current) => [
      ...current,
      {
        role: "assistant",
        content,
        visibleContent: "",
      },
    ]);

    let index = 0;
    typingIntervalRef.current = window.setInterval(() => {
      index += 3;
      const nextContent = content.slice(0, index);
      setChatMessages((current) => {
        const next = [...current];
        const lastIndex = next.length - 1;
        if (lastIndex < 0 || next[lastIndex].role !== "assistant") {
          return current;
        }
        next[lastIndex] = {
          ...next[lastIndex],
          visibleContent: nextContent,
        };
        return next;
      });

      if (index >= content.length) {
        clearTypingAnimation();
        setIsAssistantTyping(false);
      }
    }, 18);
  }

  function toggleTheme() {
    setIsDarkTheme((current) => {
      const next = !current;
      localStorage.setItem("niraconchem-theme", next ? "dark" : "light");
      return next;
    });
  }

  function updateClarification(key: keyof ClarificationAnswers, value: string) {
    setClarification((current) => ({
      ...current,
      [key]: current[key] === value && key !== "notes" ? "" : value,
    }));
  }

  function buildClarifiedQuery() {
    const details = [
      clarification.area ? `construction area: ${clarification.area}` : "",
      clarification.exposure ? `exposure: ${clarification.exposure}` : "",
      clarification.substrate ? `substrate: ${clarification.substrate}` : "",
      clarification.location ? `location: ${clarification.location}` : "",
      clarification.notes ? `additional details: ${clarification.notes}` : "",
    ].filter(Boolean);

    return details.length ? `${query.trim()}. ${details.join("; ")}.` : query.trim();
  }

  async function submitRecommendation(nextQuery = query) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) {
      setError("Enter a construction chemical requirement first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setShowClarifier(false);

    try {
      const response = await apiFetch("/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: trimmedQuery,
          document_context: fileAnalysis?.preview,
          document_name: fileAnalysis?.filename,
        }),
      });

      if (!response.ok) {
        throw new Error("Recommendation request failed.");
      }

      const data = (await response.json()) as Recommendation;
      setRecommendation(data);
      if (nextQuery !== query) {
        setQuery(nextQuery);
      }
    } catch (error) {
      setError(
        error instanceof DOMException && error.name === "AbortError"
          ? "Backend took too long to respond. Check that the deployed API is awake and the Vercel backend URL is correct."
          : "Backend is not reachable. Check NEXT_PUBLIC_API_BASE_URL, backend deployment, and CORS settings.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function submitChat(nextMessage = query) {
    const trimmedMessage = nextMessage.trim();
    if (!trimmedMessage) {
      setError("Enter a construction chemical requirement first.");
      return;
    }

    setIsLoading(true);
    setIsAssistantTyping(true);
    setError("");
    setShowClarifier(false);
    setChatMessages((current) => [...current, { role: "user", content: trimmedMessage }]);
    setQuery("");

    try {
      const response = await apiFetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmedMessage,
        }),
      });

      if (!response.ok) {
        throw new Error("Chat request failed.");
      }

      const data = (await response.json()) as ChatResponse;
      setSessionId(data.session_id);
      setLatestChat(data);
      setReportPayload(data.report_payload || null);
      animateAssistantMessage(
        [data.reply, ...data.questions.map((question) => `- ${question}`)].join(
          data.questions.length ? "\n\n" : "",
        ),
      );

      const reportQuery = data.report_payload?.query?.trim();
      if (data.report_ready && reportQuery) {
        setQuery("");
      }
    } catch (error) {
      setError(
        error instanceof DOMException && error.name === "AbortError"
          ? "NIRACONCHEM AI took too long to respond. The backend may be waking up."
          : "Chat backend is not reachable. Check NEXT_PUBLIC_API_BASE_URL, backend deployment, and CORS settings.",
      );
      clearTypingAnimation();
      setIsAssistantTyping(false);
      setChatMessages((current) => current.slice(0, -1));
      setQuery(trimmedMessage);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a construction chemical requirement first.");
      return;
    }
    void submitChat(trimmedQuery);
  }

  function handleExample(example: string) {
    setQuery(example);
    setShowClarifier(false);
    void submitChat(example);
  }

  function submitWithClarification() {
    void submitRecommendation(buildClarifiedQuery());
  }

  function skipClarification() {
    void submitRecommendation(query);
  }

  async function installApp() {
    if (!installPrompt) {
      return;
    }

    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome !== "dismissed") {
      setInstallPrompt(null);
    }
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsAnalyzingFile(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch("/analyze-file", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("File analysis failed.");
      }

      const data = (await response.json()) as FileAnalysis;
      setFileAnalysis(data);
    } catch (error) {
      setError(
        error instanceof DOMException && error.name === "AbortError"
          ? "File analysis took too long. Check that the deployed backend is running."
          : "Could not read that file. Check the backend URL, CORS, and file type.",
      );
      setFileAnalysis(null);
    } finally {
      setIsAnalyzingFile(false);
      event.target.value = "";
    }
  }

  function clearFileAnalysis() {
    setFileAnalysis(null);
  }

  async function downloadReport() {
    const trimmedQuery = reportPayload?.query?.trim() || query.trim();
    if (!trimmedQuery) {
      setError("Generate a recommendation before downloading a PDF.");
      return;
    }

    setIsDownloading(true);
    setError("");

    try {
      const response = await apiFetch("/recommend/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: trimmedQuery,
          document_context: reportPayload?.document_context || fileAnalysis?.preview,
          document_name: reportPayload?.document_name || fileAnalysis?.filename,
        }),
      });

      if (!response.ok) {
        throw new Error("PDF request failed.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "niraconchem-recommendation.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setError(
        error instanceof DOMException && error.name === "AbortError"
          ? "PDF generation took too long. Check that the deployed backend is running."
          : "Could not download the PDF report. Check the backend URL and CORS settings.",
      );
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <main className={`home${hasChatStarted ? " has-result" : ""}${isDarkTheme ? " dark-theme" : ""}`}>
      <button
        aria-label={isDarkTheme ? "Switch to light theme" : "Switch to dark theme"}
        className="theme-toggle"
        onClick={toggleTheme}
        title={isDarkTheme ? "Light theme" : "Dark theme"}
        type="button"
      >
        <span className="theme-toggle-symbol theme-toggle-sun" aria-hidden="true">
          <Sun size={17} strokeWidth={2.2} />
        </span>
        <span className="theme-toggle-symbol theme-toggle-moon" aria-hidden="true">
          <Moon size={18} strokeWidth={2.2} />
        </span>
        <span className="theme-toggle-knob" aria-hidden="true" />
      </button>
      {installPrompt ? (
        <button className="app-install-button" onClick={installApp} type="button">
          Install
        </button>
      ) : null}
      <ParticleWaveBackground />
      <header className="topbar">
        <div className="logo-card" aria-label="NIRACONCHEM chemistry logo">
          <img
            className="atom-logo"
            src="/assets/atom-logo-transparent.png.png"
            alt="NIRACONCHEM chemistry logo"
          />
        </div>
        <p className="assistant-label">Ask for UAE-ready construction chemical guidance</p>
      </header>

      <section className={`search-stage${hasChatStarted ? " has-result" : ""}`} aria-label="Construction chemicals search">
        <form className="search-box" onSubmit={handleSubmit}>
          <label className="upload-icon-button" htmlFor="project-file" title="Upload project file">
            <Paperclip size={20} strokeWidth={2.2} aria-hidden="true" />
          </label>
          <input
            accept=".pdf,.docx,.xlsx,.txt"
            disabled={isAnalyzingFile}
            id="project-file"
            onChange={handleFileUpload}
            type="file"
          />
          <input
            aria-label="Construction chemical recommendation query"
            className="query-input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Chat: I need waterproofing, Dubai basement concrete, hydrostatic water pressure..."
            type="search"
            value={query}
          />
          <button disabled={isLoading || isAssistantTyping} type="submit">
            {isLoading ? "Thinking" : "Send"}
          </button>
        </form>
        <div className="quick-prompts" aria-label="Example searches">
          {examples.map((example) => (
            <button key={example} onClick={() => handleExample(example)} type="button">
              {example}
            </button>
          ))}
        </div>

        {showClarifier ? (
          <div className="clarifier-panel" aria-label="Project clarification questions">
            <div className="clarifier-header">
              <span>Project details</span>
              <p>Add a few details so the agent can match the datasheets more accurately.</p>
            </div>
            <div className="clarifier-grid">
              <section>
                <h3>Construction area</h3>
                <div className="clarifier-options">
                  {clarificationOptions.area.map((option) => (
                    <button
                      className={clarification.area === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("area", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Exposure condition</h3>
                <div className="clarifier-options">
                  {clarificationOptions.exposure.map((option) => (
                    <button
                      className={clarification.exposure === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("exposure", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Substrate</h3>
                <div className="clarifier-options">
                  {clarificationOptions.substrate.map((option) => (
                    <button
                      className={clarification.substrate === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("substrate", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Project location</h3>
                <div className="clarifier-options">
                  {clarificationOptions.location.map((option) => (
                    <button
                      className={clarification.location === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("location", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
            </div>
            <textarea
              aria-label="Additional project notes"
              className="clarifier-notes"
              onChange={(event) => updateClarification("notes", event.target.value)}
              placeholder="Optional: add thickness, crack width, new/old concrete, traffic level, water pressure, or specification requirement..."
              value={clarification.notes}
            />
            <div className="clarifier-actions">
              <button disabled={isLoading} onClick={submitWithClarification} type="button">
                Recommend with details
              </button>
              <button disabled={isLoading} onClick={skipClarification} type="button">
                Skip questions
              </button>
            </div>
          </div>
        ) : null}

        {fileAnalysis ? (
          <div className="file-summary">
            <div>
              <strong>{fileAnalysis.filename}</strong>
              <span>{fileAnalysis.extracted_characters} characters extracted</span>
            </div>
            <button onClick={clearFileAnalysis} type="button">
              Remove
            </button>
            <p>{fileAnalysis.preview}</p>
            <ul>
              {[...fileAnalysis.locations, ...fileAnalysis.construction_areas, ...fileAnalysis.requirements]
                .slice(0, 8)
                .map((item) => (
                  <li key={item}>{item}</li>
                ))}
            </ul>
          </div>
        ) : null}

        {error ? <p className="error-text">{error}</p> : null}

        {hasChatStarted ? (
        <section className="chat-panel" aria-label="NIRACONCHEM AI chat">
          <div className="chat-header">
            <span>NIRACONCHEM AI Consultant</span>
            {latestChat?.report_ready ? <strong>Report ready</strong> : <strong>Collecting project data</strong>}
          </div>
          <div className="chat-messages">
  {chatMessages.map((message, index) => (
    <div
      className={`chat-message ${message.role}`}
      key={`${message.role}-${index}`}
    >
      <span className="chat-avatar" aria-hidden="true">
        {message.role === "assistant" ? (
          <Bot size={16} />
        ) : (
          <User size={16} />
        )}
      </span>

      <p>
        {message.visibleContent ?? message.content}
        {message.role === "assistant" &&
        message.visibleContent !== undefined &&
        message.visibleContent.length < message.content.length ? (
          <span className="typing-cursor" aria-hidden="true" />
        ) : null}
      </p>
    </div>
  ))}
</div>
            {isAssistantTyping && chatMessages.at(-1)?.role === "user" ? (
              <div className="chat-message assistant typing-preview">
                <span className="chat-avatar" aria-hidden="true">
                  <Bot size={16} />
                </span>
                <p aria-label="NIRACONCHEM AI is typing">
                  <span />
                  <span />
                  <span />
                </p>
              </div>
            ) : null}
          </div>
          {latestChat ? (
            <div className="chat-status">
              <div>
                <strong>Captured</strong>
                <span>
                  {Object.entries(latestChat.requirements)
                    .filter(([, value]) => value)
                    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`)
                    .join(" â€¢ ") || "Waiting for project details"}
                </span>
              </div>
              {latestChat.missing_requirements.length ? (
                <div>
                  <strong>Needed</strong>
                  <span>{latestChat.missing_requirements.join(", ")}</span>
                </div>
              ) : null}
            </div>
          ) : null}
          {latestChat?.report_ready ? (
            <button className="download-button" disabled={isDownloading} onClick={downloadReport} type="button">
              {isDownloading ? "Preparing PDF" : "Download PDF Report"}
            </button>
          ) : null}
        </section>
        ) : null}

      </section>
    </main>
  );
}


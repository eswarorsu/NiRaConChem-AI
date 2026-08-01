"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { MoreVertical, Moon, Paperclip, SendHorizontal, Sun, Trash2, LogIn, X, Mail, Lock, UserPlus, ArrowRight, Download } from "lucide-react";
import BlinkingEyes from "./components/BlinkingEyes";
import ClassicUserAvatar from "./components/ClassicUserAvatar";
import { ParticleWaveBackground } from "./components/ParticleWaveBackground";
import BrandScroller from "./components/BrandScroller";
import qconMarketData from "./data/qcon-market-products.json";

const RENDER_API_BASE_URL = "https://niraconchem-ai.onrender.com";
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const API_BASE_URL =
  process.env.NODE_ENV === "development"
    ? configuredApiBaseUrl || "http://localhost:8000"
    : configuredApiBaseUrl?.includes("onrender.com")
      ? configuredApiBaseUrl
      : RENDER_API_BASE_URL;
const API_TIMEOUT_MS = 45000;

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

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

type MarketProduct = {
  id: string;
  name: string;
  company: string;
  brand: string;
  category: string;
  url: string;
  imageUrl: string;
  localImage: string;
  description: string;
  price: string;
  keywords: string[];
};

type ActiveMode = "nira" | "market";

const examples = [
  "I need waterproofing",
  "Dubai basement concrete hydrostatic pressure",
  "Parking deck coating with vehicle traffic",
];

const broadTerms = ["waterproofing", "flooring", "repair", "coating", "sealant", "tile adhesive", "chemical"];
const areaTerms = ["roof", "rooftop", "basement", "bathroom", "wet", "parking", "floor", "joint", "tank", "pool", "wall", "slab", "villa"];
const exposureTerms = ["uv", "heat", "traffic", "chemical", "chloride", "coastal", "water", "pressure", "potable", "external", "interior", "crack"];
const substrateTerms = ["concrete", "screed", "tile", "metal", "block", "masonry", "plaster"];
const constructionTerms = [
  ...broadTerms,
  ...areaTerms,
  ...exposureTerms,
  ...substrateTerms,
  "construction",
  "building",
  "site",
  "project",
  "datasheet",
  "specification",
  "membrane",
  "epoxy",
  "polyurethane",
  "cementitious",
  "grout",
  "anchor",
  "adhesive",
  "joint",
  "waterproof",
];

function displayValue(value?: string | null) {
  return value && value.trim() ? value : "Not specified in retrieved datasheet";
}

function includesAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function isConstructionRelatedQuery(value: string) {
  const normalized = value.toLowerCase().trim();
  return includesAny(normalized, constructionTerms);
}

function tokenizeMarketText(value: string) {
  const normalized = value
    .toLowerCase()
    .replace(/\bwater\s+proof(?:ing)?\b/g, "waterproofing")
    .replace(/\bfix(?:ing)?\s+tiles?\b/g, "tile adhesive")
    .replace(/\btiles?\s+fix(?:ing)?\b/g, "tile adhesive")
    .replace(/\btails?\b/g, "tiles")
    .replace(/\bconcrate\b/g, "concrete");

  const terms = normalized
    .split(/[^a-z0-9]+/)
    .filter((term) => term.length > 2);

  if (normalized.includes("waterproof") || normalized.includes("leak") || normalized.includes("bathroom") || normalized.includes("basement") || normalized.includes("roof")) {
    terms.push("waterproof", "waterproofing", "membrane", "sealant", "primer", "coating", "roof", "basement", "wet", "tank", "pool");
  }
  if (normalized.includes("floor") || normalized.includes("parking") || normalized.includes("traffic") || normalized.includes("warehouse")) {
    terms.push("flooring", "floor", "coating", "screed", "epoxy", "polyurethane", "deck");
  }
  if (normalized.includes("tile") || normalized.includes("adhesive") || normalized.includes("grout")) {
    terms.push("tile", "tiles", "adhesive", "grout", "sealer", "primer", "porcelain", "ceramic");
  }
  if (normalized.includes("repair") || normalized.includes("crack") || normalized.includes("honeycomb") || normalized.includes("spall")) {
    terms.push("repair", "concrete", "mortar", "grout", "crack", "epoxy");
  }
  if (normalized.includes("joint") || normalized.includes("sealant") || normalized.includes("expansion")) {
    terms.push("joint", "sealant", "polyurethane", "backer", "primer");
  }

  return [...new Set(terms)];
}

function scoreMarketProduct(product: MarketProduct, searchText: string) {
  const terms = tokenizeMarketText(searchText);
  const name = product.name.toLowerCase();
  const category = product.category.toLowerCase();
  const description = product.description.toLowerCase();
  const keywordText = product.keywords.join(" ");
  const brand = `${product.brand} ${product.company}`.toLowerCase();

  return terms.reduce((score, term) => {
    if (name.includes(term)) return score + 7;
    if (category.includes(term)) return score + 5;
    if (brand.includes(term)) return score + 3;
    if (keywordText.includes(term)) return score + 3;
    if (description.includes(term)) return score + 2;
    return score;
  }, 0);
}

function inferNaturalChatReply(query: string) {
  const normalized = query.toLowerCase();
  const sections: { title: string; guidance: string[] }[] = [];

  if (normalized.includes("tile") || normalized.includes("adhesive") || normalized.includes("grout") || normalized.includes("fix")) {
    sections.push({
      title: "Tile Fixing / Grouting",
      guidance: [
        "clean the surface and remove dust, oil, weak plaster, or laitance",
        "use the correct installation method for the selected material",
        "allow the installed system to cure as required by the datasheet",
      ],
    });
  }

  if (normalized.includes("water") || normalized.includes("leak") || normalized.includes("roof") || normalized.includes("basement") || normalized.includes("bathroom") || normalized.includes("pool") || normalized.includes("tank")) {
    sections.push({
      title: "Waterproofing",
      guidance: [
        "confirm whether the water pressure is positive, negative, or hydrostatic",
        "treat cracks, corners, pipe penetrations, and construction joints first",
        "check required thickness, coverage, curing, and test requirements",
      ],
    });
  }

  if (normalized.includes("floor") || normalized.includes("parking") || normalized.includes("traffic") || normalized.includes("warehouse") || normalized.includes("epoxy") || normalized.includes("pu")) {
    sections.push({
      title: "Flooring / Coating",
      guidance: [
        "check concrete moisture, surface strength, and contamination before coating",
        "select the system by traffic load, UV, exposure, and slip resistance",
        "prepare the surface as required by the datasheet",
      ],
    });
  }

  if (normalized.includes("repair") || normalized.includes("crack") || normalized.includes("honeycomb") || normalized.includes("spall")) {
    sections.push({
      title: "Concrete Repair",
      guidance: [
        "remove loose concrete and clean reinforcement before repair",
        "confirm whether cracks are active, dormant, structural, or non-structural",
        "cure repair mortar correctly, especially in hot site conditions",
      ],
    });
  }

  if (normalized.includes("joint") || normalized.includes("sealant") || normalized.includes("expansion")) {
    sections.push({
      title: "Sealant / Joint Treatment",
      guidance: [
        "confirm joint width, depth, movement, and exposure",
        "clean and prime joint faces before sealant application",
        "use backer rod to control sealant depth and avoid three-side adhesion",
      ],
    });
  }

  const selected = sections.length
    ? sections
    : [
        {
          title: "Construction Chemical Selection",
          guidance: [
            "confirm the application area, substrate, exposure, and location",
            "match the product category to the actual site condition",
            "verify the final selection against the datasheet",
          ],
        },
      ];

  const first = selected[0];
  return [
    `Based on your query, this looks like a ${selected.map((section) => section.title).join(" + ")} requirement.`,
    "Next Details Needed\n- application area\n- substrate\n- exposure condition\n- project location",
    `Application Notes\n${first.guidance.map((item) => `- ${item}`).join("\n")}`,
    "MARKET RESULT is ready for matched options. The chat will only handle project inputs and guidance.",
  ].join("\n\n");
}

function normalizeChatReply(reply: string, query: string) {
  // Only rewrite the legacy inert template. Detect it by its exact signature so
  // genuine RAG answers (which legitimately contain numbered lists, AED prices,
  // or URLs) are shown verbatim instead of being replaced with canned text.
  const isLegacyTemplate =
    reply.includes("MARKET RESULT is ready for matched options") ||
    reply.includes("Next Details Needed");
  if (isLegacyTemplate) {
    return inferNaturalChatReply(query);
  }
  return reply;
}

function renderAssistantContent(content: string, showCursor: boolean) {
  const blocks = content.split(/\n{2,}/).filter((block) => block.trim());

  return (
    <div className="chat-answer">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").filter((line) => line.trim());
        const isList = lines.every((line) => /^[-*•]\s+/.test(line.trim()));
        const hasHeadingWithList = lines.length > 1 && !/^[-*•]\s+/.test(lines[0].trim()) && lines.slice(1).every((line) => /^[-*•]\s+/.test(line.trim()));

        if (isList) {
          return (
            <ul className="chat-answer-list" key={`${block}-${blockIndex}`}>
              {lines.map((line, lineIndex) => (
                <li key={`${line}-${lineIndex}`}>{line.replace(/^[-*•]\s+/, "")}</li>
              ))}
            </ul>
          );
        }

        if (hasHeadingWithList) {
          return (
            <section className="chat-answer-section" key={`${block}-${blockIndex}`}>
              <strong>{lines[0]}</strong>
              <ul className="chat-answer-list">
                {lines.slice(1).map((line, lineIndex) => (
                  <li key={`${line}-${lineIndex}`}>{line.replace(/^[-*•]\s+/, "")}</li>
                ))}
              </ul>
              {showCursor && blockIndex === blocks.length - 1 ? <span className="typing-cursor" aria-hidden="true" /> : null}
            </section>
          );
        }

        const text = lines.join(" ");
        const [label, ...rest] = text.split(":");
        const hasShortLabel = rest.length > 0 && label.length <= 34;

        return (
          <p className={blockIndex === 0 ? "chat-answer-lead" : ""} key={`${text}-${blockIndex}`}>
            {hasShortLabel ? (
              <>
                <strong>{label}:</strong>
                {rest.join(":")}
              </>
            ) : (
              text
            )}
            {showCursor && blockIndex === blocks.length - 1 ? <span className="typing-cursor" aria-hidden="true" /> : null}
          </p>
        );
      })}
      {showCursor && blocks.length === 0 ? <span className="typing-cursor" aria-hidden="true" /> : null}
    </div>
  );
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
  const [fileAnalysis, setFileAnalysis] = useState<FileAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzingFile, setIsAnalyzingFile] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [isProjectQuery, setIsProjectQuery] = useState(false);
  const [activeMode, setActiveMode] = useState<ActiveMode>("nira");
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [error, setError] = useState("");
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const typingIntervalRef = useRef<number | null>(null);
  const hasChatStarted = chatMessages.some((message) => message.role === "user");
  const latestUserMessage = [...chatMessages].reverse().find((message) => message.role === "user")?.content || query;
  const marketSearchText = [
    latestUserMessage,
    latestChat?.reply || "",
    latestChat ? Object.values(latestChat.requirements).filter(Boolean).join(" ") : "",
  ].join(" ");
  const marketProducts = useMemo(() => {
    const products = (qconMarketData.products as MarketProduct[])
      .map((product) => ({
        product,
        score: scoreMarketProduct(product, marketSearchText),
      }))
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score || a.product.name.localeCompare(b.product.name))
      .slice(0, 12)
      .map(({ product }) => product);

    return products.length ? products : (qconMarketData.products as MarketProduct[]).slice(0, 8);
  }, [marketSearchText]);

  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginMode, setLoginMode] = useState<"login" | "register">("login");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginConfirmPassword, setLoginConfirmPassword] = useState("");

  useEffect(() => {
    if (!showMoreMenu) return;

    function handleOutsideClick(event: MouseEvent) {
      const target = event.target as HTMLElement;
      if (!target.closest(".more-options-button") && !target.closest(".more-options-menu")) {
        setShowMoreMenu(false);
      }
    }

    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, [showMoreMenu]);

  function handleClearChat() {
    setChatMessages([]);
    setSessionId(null);
    setLatestChat(null);
    setReportPayload(null);
    setFileAnalysis(null);
    setQuery("");
    setError("");
    setShowMoreMenu(false);
  }

  function handleLoginClick() {
    setShowMoreMenu(false);
    setLoginMode("login");
    setLoginEmail("");
    setLoginPassword("");
    setLoginConfirmPassword("");
    setShowLoginModal(true);
  }

  function handleCloseLoginModal() {
    setShowLoginModal(false);
    setLoginEmail("");
    setLoginPassword("");
    setLoginConfirmPassword("");
  }

  function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loginMode === "register" && loginPassword !== loginConfirmPassword) {
      alert("Passwords do not match!");
      return;
    }
    // Placeholder â€” wire up real auth here
    alert(`${loginMode === "login" ? "Login" : "Registration"} submitted for: ${loginEmail}`);
    handleCloseLoginModal();
  }

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

  async function submitChat(nextMessage = query) {
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
      const normalizedData = {
        ...data,
        reply: normalizeChatReply(data.reply, trimmedMessage),
      };
      setSessionId(normalizedData.session_id);
      setLatestChat(normalizedData);
      setReportPayload(normalizedData.report_payload || null);
      animateAssistantMessage(normalizedData.reply);

      const reportQuery = normalizedData.report_payload?.query?.trim();
      if (normalizedData.intent === "technical_consultation" && !normalizedData.needs_clarification) {
        setActiveMode("market");
      }
      if (normalizedData.report_ready && reportQuery) {
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
    void submitChat(example);
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
        <button className="app-install-button" onClick={installApp} type="button" title="Install App">
          <span className="install-text">Install</span>
          <span className="install-icon" aria-hidden="true">
            <Download size={18} strokeWidth={2.4} />
          </span>
        </button>
      ) : null}
      <button
        aria-label="More options"
        className={`more-options-button${showMoreMenu ? " active" : ""}`}
        onClick={() => setShowMoreMenu((prev) => !prev)}
        title="More options"
        type="button"
      >
        <MoreVertical size={24} strokeWidth={2.4} aria-hidden="true" />
      </button>

      {showMoreMenu ? (
        <div className="more-options-menu" role="menu">
          <button
            className="menu-item"
            onClick={handleClearChat}
            role="menuitem"
            type="button"
          >
            <Trash2 size={16} strokeWidth={2.2} />
            <span>Clear Chat</span>
          </button>
          <button
            className="menu-item"
            onClick={handleLoginClick}
            role="menuitem"
            type="button"
          >
            <LogIn size={16} strokeWidth={2.2} />
            <span>Log In</span>
          </button>
        </div>
      ) : null}

      {showLoginModal ? (
        <div className="login-modal-overlay" role="dialog" aria-modal="true" aria-label={loginMode === "login" ? "Log in" : "Create account"} onClick={(e) => { if ((e.target as HTMLElement).classList.contains("login-modal-overlay")) handleCloseLoginModal(); }}>
          <div className="login-modal-card">
            <div className="login-modal-glow" />
            <button className="login-modal-close" aria-label="Close" onClick={handleCloseLoginModal} type="button">
              <X size={18} strokeWidth={2.2} />
            </button>

            <div className="login-modal-header">
              <div className="login-brand-mark" aria-hidden="true">
                <span className="login-brand-orbit" />
                <LogIn size={18} strokeWidth={2.2} />
              </div>
              <h2>{loginMode === "login" ? "Welcome back" : "Create account"}</h2>
              <p>{loginMode === "login" ? "Sign in to your account" : "Sign up for an account"}</p>
            </div>

            <form className="login-modal-form" onSubmit={handleLoginSubmit}>
              <div className="login-field-pill">
                <span className="login-field-pill-label">Email</span>
                <div className="login-field-row">
                  <Mail size={18} className="login-field-icon" strokeWidth={2} />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    placeholder="username@gmail.com"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="login-field-pill">
                <span className="login-field-pill-label">Password</span>
                <div className="login-field-row">
                  <Lock size={18} className="login-field-icon" strokeWidth={2} />
                  <input
                    id="login-password"
                    type="password"
                    autoComplete={loginMode === "login" ? "current-password" : "new-password"}
                    placeholder="••••••••"
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                  />
                </div>
              </div>

              {loginMode === "register" ? (
                <div className="login-field-pill">
                  <span className="login-field-pill-label">Confirm Password</span>
                  <div className="login-field-row">
                    <Lock size={18} className="login-field-icon" strokeWidth={2} />
                    <input
                      id="login-confirm-password"
                      type="password"
                      autoComplete="new-password"
                      placeholder="••••••••"
                      required
                      value={loginConfirmPassword}
                      onChange={(e) => setLoginConfirmPassword(e.target.value)}
                    />
                  </div>
                </div>
              ) : null}

              <button className="login-submit-pill" type="submit">
                <span>{loginMode === "login" ? "Continue" : "Register"}</span>
                <ArrowRight size={18} strokeWidth={2.2} />
              </button>
            </form>

            <div className="login-divider">
              <span className="login-divider-line"></span>
              <span className="login-divider-text">OR</span>
              <span className="login-divider-line"></span>
            </div>

            <div className="social-login-group">
              <button type="button" className="social-login-button" onClick={() => alert("Google Sign-In is not configured for this environment.")}>
                <svg className="social-icon" viewBox="0 0 24 24" width="18" height="18">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>Continue with Google</span>
                <ArrowRight size={16} className="social-arrow" />
              </button>

              <button type="button" className="social-login-button" onClick={() => alert("X Sign-In is not configured for this environment.")}>
                <svg className="social-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
                <span>Continue with X</span>
                <ArrowRight size={16} className="social-arrow" />
              </button>
            </div>

            <div className="login-modal-footer">
              {loginMode === "login" ? (
                <>
                  <span>Don't have an account?</span>
                  <button type="button" onClick={() => setLoginMode("register")}>Sign up</button>
                </>
              ) : (
                <>
                  <span>Already have an account?</span>
                  <button type="button" onClick={() => setLoginMode("login")}>Sign in</button>
                </>
              )}
            </div>
          </div>
        </div>
      ) : null}
      {hasChatStarted ? (
        <nav className="mode-toolbar" aria-label="Platform mode">
          <button className={activeMode === "nira" ? "active" : ""} onClick={() => setActiveMode("nira")} type="button">
            NIRA AI
          </button>
          <button className={activeMode === "market" ? "active" : ""} onClick={() => setActiveMode("market")} type="button">
            MARKET RESULT
          </button>
        </nav>
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
        <h1 className="consultant-title">NIRACONCHEM AI</h1>
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
            <span>{isLoading ? "Thinking" : "Send"}</span>
            <SendHorizontal size={17} strokeWidth={2.4} aria-hidden="true" />
          </button>
        </form>
        <div className="quick-prompts" aria-label="Example searches">
          {examples.map((example) => (
            <button key={example} onClick={() => handleExample(example)} type="button">
              {example}
            </button>
          ))}
        </div>

        {/* 3D brand marquee — visible until the user starts a search, then disappears */}
        <BrandScroller visible={!hasChatStarted} />


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
            <span>{activeMode === "market" ? "NIRACONCHEM Market Results" : "NIRACONCHEM AI Consultant"}</span>
            {activeMode === "market" ? (
              <strong>{marketProducts.length} matches</strong>
            ) : isProjectQuery ? (
              latestChat?.report_ready ? <strong>Report ready</strong> : <strong>Collecting project data</strong>
            ) : (
              <strong>General answer</strong>
            )}
          </div>
          {activeMode === "market" ? (
            <div className="market-results" aria-label="Market result products">
              <div className="market-summary">
                <strong>NIRACONCHEM market results and experts recommendation</strong>
                <span>{isProjectQuery ? "Ranked from your query and AI project context" : "Enter a construction chemical query for tighter matching"}</span>
              </div>
              <div className="market-grid">
                {marketProducts.map((product) => (
                  <a className="market-card" href={product.url} key={product.url} rel="noreferrer" target="_blank">
                    <span className="market-image">
                      <img alt={product.name} src={product.localImage || product.imageUrl || "/assets/atom-logo-transparent.png.png"} />
                    </span>
                    <span className="market-card-body">
                      <span className="market-brand">{product.company}</span>
                      <strong>{product.name}</strong>
                      <span>{product.category}</span>
                      {product.description ? <p>{product.description}</p> : null}
                      {product.price ? <em>{product.price}</em> : null}
                    </span>
                  </a>
                ))}
              </div>
            </div>
          ) : (
            <>
            <div className="chat-messages">
              {chatMessages.map((message, index) => (
                <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                  <span className="chat-avatar" aria-hidden="true">
                    {message.role === "assistant" ? <BlinkingEyes /> : <ClassicUserAvatar />}
                  </span>
                  {message.role === "assistant" ? (
                    renderAssistantContent(
                      message.visibleContent ?? message.content,
                      message.visibleContent !== undefined && message.visibleContent.length < message.content.length,
                    )
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
              ))}
              {isAssistantTyping && chatMessages.at(-1)?.role === "user" ? (
                <div className="chat-message assistant typing-preview">
                  <span className="chat-avatar" aria-hidden="true">
                    <BlinkingEyes />
                  </span>
                  <p aria-label="NIRACONCHEM AI is typing">
                    <span />
                    <span />
                    <span />
                  </p>
                </div>
              ) : null}
            </div>
          {latestChat?.report_ready && isProjectQuery ? (
            <button className="download-button" disabled={isDownloading} onClick={downloadReport} type="button">
              {isDownloading ? "Preparing PDF" : "Download PDF Report"}
            </button>
          ) : null}
            </>
          )}
        </section>
        ) : null}

      </section>
    </main>
  );
}

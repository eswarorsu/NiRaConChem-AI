import type { ChatResponse, FileAnalysis } from "./types";

const RENDER_API_BASE_URL = "https://niraconchem-ai.onrender.com";
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

/** An explicitly configured URL always wins, in every mode. A production build
 *  used to discard NEXT_PUBLIC_API_BASE_URL unless it contained "onrender.com",
 *  so `npm start` against a local backend quietly called the deployed API. */
export const API_BASE_URL =
  configuredApiBaseUrl ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : RENDER_API_BASE_URL);

export const API_TIMEOUT_MS = 45000;

/** Every call is bounded: the backend sleeps on the free Render tier and an
 *  unbounded fetch leaves the UI spinning with no way back. */
async function withTimeout<T>(run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await run(controller.signal);
  } finally {
    window.clearTimeout(timer);
  }
}

export async function postChat(body: {
  message: string;
  session_id: string | null;
  document_context?: string;
  document_name?: string;
}): Promise<ChatResponse> {
  return withTimeout(async (signal) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    if (!response.ok) throw new Error("Chat request failed.");
    return (await response.json()) as ChatResponse;
  });
}

export async function postFileAnalysis(file: File): Promise<FileAnalysis> {
  return withTimeout(async (signal) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/analyze-file`, {
      method: "POST",
      body: formData,
      signal,
    });
    if (!response.ok) throw new Error("File analysis failed.");
    return (await response.json()) as FileAnalysis;
  });
}

export async function postReport(body: Record<string, unknown>): Promise<Blob> {
  return withTimeout(async (signal) => {
    const response = await fetch(`${API_BASE_URL}/recommend/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    if (!response.ok) throw new Error("Report generation failed.");
    return await response.blob();
  });
}

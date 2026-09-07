import type { StructuredAnswer } from "../components/AnswerCard";

/** Shapes exchanged with the FastAPI backend, plus the browser event the PWA
 *  install prompt arrives on. Extracted from page.tsx so the hook, the view
 *  components and the API client all agree on one definition. */

export type FileAnalysis = {
  filename: string;
  file_type: string;
  extracted_characters: number;
  preview: string;
  locations: string[];
  construction_areas: string[];
  requirements: string[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  /** Set while the typing animation is still catching up with `content`. */
  visibleContent?: string;
  report_ready?: boolean;
  structured?: StructuredAnswer | null;
};

export type ChatResponse = {
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
  structured?: StructuredAnswer | null;
};

export type MarketProduct = {
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

export type ActiveMode = "nira" | "market";

export type SidePanel = "chat" | "reports" | "subscription" | "profile";

export type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

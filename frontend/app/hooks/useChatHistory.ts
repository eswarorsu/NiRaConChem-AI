"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatMessage } from "../lib/types";

/**
 * Conversations kept in this browser only (localStorage) — there is no account
 * system behind the product, so nothing leaves the device. The history panel
 * lists them; opening one hands its transcript back to useChatSession.
 */

const STORAGE_KEY = "nira.history.v1";
const MAX_CONVERSATIONS = 40;

export type SavedConversation = {
  id: string;
  title: string;
  updatedAt: number;
  sessionId: string | null;
  messages: ChatMessage[];
};

function read(): SavedConversation[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedConversation[];
    return Array.isArray(parsed) ? parsed.filter((item) => item && Array.isArray(item.messages)) : [];
  } catch {
    return [];
  }
}

function write(items: SavedConversation[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // Private windows and full storage both land here; history is a convenience.
  }
}

function newId() {
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
}

export function useChatHistory({
  messages,
  sessionId,
  isAssistantTyping,
}: {
  messages: ChatMessage[];
  sessionId: string | null;
  isAssistantTyping: boolean;
}) {
  const [items, setItems] = useState<SavedConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeIdRef = useRef<string | null>(null);

  useEffect(() => {
    // Storage is only readable in the browser, after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setItems(read());
  }, []);

  // Save the conversation on screen once the reply has finished typing.
  useEffect(() => {
    if (isAssistantTyping) return;
    const firstQuestion = messages.find((message) => message.role === "user");
    if (!firstQuestion) return;

    let id = activeIdRef.current;
    if (!id) {
      id = newId();
      activeIdRef.current = id;
      setActiveId(id);
    }
    const stored = read();
    const existing = stored.find((item) => item.id === id);
    // Re-opening a saved conversation must not bump it to "Today".
    if (existing && existing.messages.length === messages.length) return;
    const entry: SavedConversation = {
      id,
      title: firstQuestion.content.slice(0, 140),
      updatedAt: Date.now(),
      sessionId,
      messages: messages.map(({ visibleContent: _unused, ...message }) => message),
    };
    const next = [entry, ...stored.filter((item) => item.id !== id)].slice(0, MAX_CONVERSATIONS);
    write(next);
    setItems(next);
  }, [messages, sessionId, isAssistantTyping]);

  /** Start tracking a fresh conversation (the next question gets a new entry). */
  const startNew = useCallback(() => {
    activeIdRef.current = null;
    setActiveId(null);
  }, []);

  /** Mark a saved conversation as the one on screen. */
  const select = useCallback((id: string) => {
    activeIdRef.current = id;
    setActiveId(id);
    return read().find((item) => item.id === id) ?? null;
  }, []);

  const clear = useCallback(() => {
    write([]);
    setItems([]);
    activeIdRef.current = null;
    setActiveId(null);
  }, []);

  return { items, activeId, startNew, select, clear };
}

/** Groups for the panel, newest first: Today, Yesterday, This week, Earlier. */
export function groupByDay(items: SavedConversation[], now = Date.now()) {
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  const today = startOfToday.getTime();
  const day = 24 * 60 * 60 * 1000;
  const groups: { label: string; items: SavedConversation[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Earlier this week", items: [] },
    { label: "Older", items: [] },
  ];
  for (const item of [...items].sort((a, b) => b.updatedAt - a.updatedAt)) {
    if (item.updatedAt >= today) groups[0].items.push(item);
    else if (item.updatedAt >= today - day) groups[1].items.push(item);
    else if (item.updatedAt >= today - 6 * day) groups[2].items.push(item);
    else groups[3].items.push(item);
  }
  return groups.filter((group) => group.items.length);
}

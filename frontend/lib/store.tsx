"use client";
import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { Clause, SummaryResult, RiskItem, ChatMessage, CompareResult } from "./types";
import { createSession } from "./api";

interface DocData {
  doc_id: string;
  name: string;
  word_count: number;
  clauses: Clause[];
  summary: SummaryResult | null;
  risks: RiskItem[] | null;
  analysisStatus: "idle" | "loading" | "done" | "error";
  analysisError?: string;
}

interface CompareDocData extends DocData {
  compareResult: CompareResult | null;
  compareStatus: "idle" | "loading" | "done" | "error";
  compareError?: string;
}

interface DocContextValue {
  sessionId: string | null;
  sessionStatus: "connecting" | "ready" | "failed";
  doc: DocData | null;
  compareDoc: CompareDocData | null;
  chatHistory: ChatMessage[];
  setDoc: (d: DocData | null) => void;
  setCompareDoc: (d: CompareDocData | null) => void;
  updateDoc: (patch: Partial<DocData>) => void;
  updateCompareDoc: (patch: Partial<CompareDocData>) => void;
  setChatHistory: (h: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  resetAll: () => void;
  syncSessionId: (sid: string) => void;
}

const DocContext = createContext<DocContextValue | null>(null);

const RETRY_DELAYS_MS = [1000, 3000, 5000, 8000, 8000, 8000, 8000, 8000];

export function DocProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<"connecting" | "ready" | "failed">("connecting");
  const [doc, setDocState] = useState<DocData | null>(null);
  const [compareDoc, setCompareDocState] = useState<CompareDocData | null>(null);
  const [chatHistory, setChatHistoryState] = useState<ChatMessage[]>([]);

  useEffect(() => {
    let cancelled = false;
    const existing = typeof window !== "undefined" ? sessionStorage.getItem("ll_session_id") : null;
    if (existing) {
      setSessionId(existing);
      setSessionStatus("ready");
      return;
    }

    async function connectWithRetry() {
      for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
        try {
          const sid = await createSession();
          if (cancelled) return;
          setSessionId(sid);
          setSessionStatus("ready");
          sessionStorage.setItem("ll_session_id", sid);
          return;
        } catch {
          if (cancelled) return;
          if (attempt === RETRY_DELAYS_MS.length) {
            setSessionStatus("failed");
            return;
          }
          await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
        }
      }
    }
    connectWithRetry();
    return () => {
      cancelled = true;
    };
  }, []);

  const setDoc = useCallback((d: DocData | null) => setDocState(d), []);
  const setCompareDoc = useCallback((d: CompareDocData | null) => setCompareDocState(d), []);
  const updateDoc = useCallback((patch: Partial<DocData>) => {
    setDocState((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);
  const updateCompareDoc = useCallback((patch: Partial<CompareDocData>) => {
    setCompareDocState((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);
  const setChatHistory = useCallback(
    (h: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => {
      setChatHistoryState(h);
    },
    []
  );
  const resetAll = useCallback(() => {
    setDocState(null);
    setCompareDocState(null);
    setChatHistoryState([]);
  }, []);
  const syncSessionId = useCallback((sid: string) => {
    setSessionId((prev) => {
      if (prev === sid) return prev;
      if (typeof window !== "undefined") sessionStorage.setItem("ll_session_id", sid);
      return sid;
    });
  }, []);

  return (
    <DocContext.Provider
      value={{
        sessionId,
        sessionStatus,
        doc,
        compareDoc,
        chatHistory,
        setDoc,
        setCompareDoc,
        updateDoc,
        updateCompareDoc,
        setChatHistory,
        resetAll,
        syncSessionId,
      }}
    >
      {children}
    </DocContext.Provider>
  );
}

export function useDoc() {
  const ctx = useContext(DocContext);
  if (!ctx) throw new Error("useDoc must be used within DocProvider");
  return ctx;
}

export type { DocData, CompareDocData };

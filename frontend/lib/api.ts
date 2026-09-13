import type {
  UploadResponse,
  SummaryResult,
  RiskItem,
  ChatResponse,
  NextStepResult,
  CompareResult,
  LawyerPrepResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

export async function createSession(): Promise<string> {
  const res = await request<{ session_id: string }>("/session", { method: "POST" });
  return res.session_id;
}

export async function uploadDocument(sessionId: string, file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>(
    `/documents/upload?session_id=${encodeURIComponent(sessionId)}`,
    { method: "POST", body: form }
  );
}

export async function loadDemoDocument(
  sessionId: string,
  variant: "lease" | "lease_renewal" = "lease"
): Promise<UploadResponse> {
  return request<UploadResponse>(
    `/documents/demo?session_id=${encodeURIComponent(sessionId)}&variant=${variant}`,
    { method: "POST" }
  );
}

export async function fetchSummary(sessionId: string, docId: string): Promise<SummaryResult> {
  return request<SummaryResult>(`/documents/${sessionId}/${docId}/summary`);
}

export async function fetchRisks(sessionId: string, docId: string): Promise<{ risks: RiskItem[] }> {
  return request<{ risks: RiskItem[] }>(`/documents/${sessionId}/${docId}/risks`);
}

export async function sendChatMessage(
  sessionId: string,
  docId: string,
  message: string,
  history: { role: string; text: string }[]
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, doc_id: docId, message, history }),
  });
}

export async function fetchNextSteps(
  sessionId: string,
  docId: string,
  question?: string
): Promise<NextStepResult> {
  return request<NextStepResult>("/next-steps", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, doc_id: docId, question }),
  });
}

export async function compareDocuments(
  sessionId: string,
  docIdA: string,
  docIdB: string
): Promise<CompareResult> {
  return request<CompareResult>("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, doc_id_a: docIdA, doc_id_b: docIdB }),
  });
}

export async function generateLawyerPrep(
  sessionId: string,
  docId: string,
  concern?: string
): Promise<LawyerPrepResult> {
  return request<LawyerPrepResult>("/lawyer-prep", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, doc_id: docId, concern }),
  });
}

export { ApiError };

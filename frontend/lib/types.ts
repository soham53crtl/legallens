export interface Clause {
  id: string;
  heading: string;
  text: string;
}

export interface UploadResponse {
  session_id: string;
  doc_id: string;
  name: string;
  word_count: number;
  clauses: Clause[];
}

export interface ImportantDate {
  label: string;
  detail: string;
  clauseId?: string | null;
}

export interface SummaryResult {
  documentType: string;
  summary: string;
  obligations: string[];
  rights: string[];
  payments: string[];
  importantDates: ImportantDate[];
  restrictions: string[];
  terminationConditions: string[];
  consequences: string[];
  missingOrInconsistent: string[];
}

export type Severity = "high" | "medium" | "standard";

export interface RiskItem {
  clauseId?: string | null;
  title: string;
  category: string;
  severity: Severity;
  explanation: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  citedClauses?: string[];
  documentSupport?: "full" | "partial" | "none";
  retrievedClauses?: string[];
}

export interface ChatResponse {
  answer: string;
  citedClauses: string[];
  documentSupport: "full" | "partial" | "none";
  retrievedClauses: string[];
}

export interface NextStepResult {
  steps: string[];
  rationale?: string | null;
}

export interface DiffEntry {
  kind: "added" | "removed" | "modified" | "unchanged";
  clause_id_a?: string | null;
  clause_id_b?: string | null;
  similarity?: number | null;
  text_a?: string | null;
  text_b?: string | null;
}

export interface CompareResult {
  computedDiff: DiffEntry[];
  added: string[];
  removed: string[];
  changedWording: string[];
  changedAmounts: string[];
  changedDates: string[];
  changedObligations: string[];
  changedTermination: string[];
}

export interface KeyClause {
  clauseId: string;
  title: string;
}

export interface LawyerPrepResult {
  documentType: string;
  keyClauses: KeyClause[];
  importantDates: ImportantDate[];
  potentialIssues: string[];
  questions: string[];
}

export interface DocState {
  doc_id: string;
  name: string;
  word_count: number;
  clauses: Clause[];
  summary: SummaryResult | null;
  risks: RiskItem[] | null;
}

/**
 * TypeScript types for the Financial Q&A system.
 * These match the backend Pydantic models.
 */

export type QueryType = "market" | "knowledge";

export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  answer: string;
  data_section: string | null;
  analysis_section: string;
  sources: string[];
  query_type: QueryType;
  ticker: string | null;
  latency_ms: number | null;
  source_type?: string | null;
}

export interface ApiError {
  detail: string;
}

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  query_type?: QueryType;
  data_section?: string | null;
  analysis_section?: string;
  sources?: string[];
  ticker?: string | null;
  latency_ms?: number | null;
  source_type?: string | null;
  timestamp: Date;
  error?: boolean;
}

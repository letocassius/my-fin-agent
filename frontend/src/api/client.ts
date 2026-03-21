/**
 * API client for the Financial Q&A backend.
 */

import type { QueryRequest, QueryResponse } from "../types";

const DEFAULT_LOCAL_API_URL = "http://localhost:8000";

function getApiBaseUrl(): string {
  const configuredUrl = import.meta.env.VITE_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/$/, "");
  }

  if (import.meta.env.DEV) {
    return DEFAULT_LOCAL_API_URL;
  }

  return window.location.origin.replace(/\/$/, "");
}

const API_BASE_URL = getApiBaseUrl();

export class ApiClientError extends Error {
  status: number;
  detail: string | undefined;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Send a financial query to the backend and return the structured response.
 */
export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? errorBody.message;
    } catch {
      detail = response.statusText;
    }
    throw new ApiClientError(
      `Request failed with status ${response.status}`,
      response.status,
      detail
    );
  }

  const data: QueryResponse = await response.json();
  return data;
}

/**
 * Check backend health.
 */
export async function checkHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new ApiClientError("Health check failed", response.status);
  }
  return response.json();
}

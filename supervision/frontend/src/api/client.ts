export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
  } | null;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (!envelope.success || envelope.data === null) {
    throw new Error(envelope.error?.message ?? "API request failed");
  }
  return envelope.data;
}

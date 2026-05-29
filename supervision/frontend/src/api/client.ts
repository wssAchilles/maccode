export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
  } | null;
}

const configuredBaseUrl = String(import.meta.env.VITE_API_BASE_URL ?? "").trim();
const API_BASE_URL = configuredBaseUrl || (import.meta.env.PROD ? "http://127.0.0.1:8000" : "");

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const headers = isFormData
    ? init?.headers
    : {
        "Content-Type": "application/json",
        ...init?.headers
      };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    });
  } catch {
    const target = API_BASE_URL ? `${API_BASE_URL}${path}` : path;
    throw new Error(`无法连接后端 API：${target}。请确认 FastAPI 后端已在 8000 端口运行。`);
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (!envelope.success || envelope.data === null) {
    throw new Error(envelope.error?.message ?? "API request failed");
  }
  return envelope.data;
}

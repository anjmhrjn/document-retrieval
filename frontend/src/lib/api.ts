const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Request failed");
  }

  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }

  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function register(name: string, email: string, password: string) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function getMe() {
  return request<{ id: number; name: string; email: string }>("/auth/me");
}

export function logout() {
  localStorage.removeItem("token");
  window.location.href = "/login";
}

// ── Documents ─────────────────────────────────────────────────────────────────

export async function getDocuments() {
  return request<Document[]>("/ingest/documents");
}

export async function uploadDocument(formData: FormData) {
  return request("/ingest/", {
    method: "POST",
    body: formData,
  });
}

export async function deleteDocument(id: number) {
  return request(`/ingest/documents/${id}`, { method: "DELETE" });
}

// ── Search ────────────────────────────────────────────────────────────────────

export interface SearchResult {
  qdrant_id: string;
  score: number;
  content: string;
  document_id: number;
  filename: string;
  source: string | null;
  category: string | null;
  client: string | null;
  chunk_index: number;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResult[];
}

export async function search(
  query: string,
  top_k = 10,
  filters: { source?: string; category?: string; client?: string } = {}
): Promise<SearchResponse> {
  return request("/search/", {
    method: "POST",
    body: JSON.stringify({ query, top_k, ...filters }),
  });
}

export interface Document {
  id: number;
  filename: string;
  file_type: string;
  source: string | null;
  category: string | null;
  client: string | null;
  upload_time: string;
}
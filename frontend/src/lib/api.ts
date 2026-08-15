const API_BASE = "";

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("kokkopi_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("kokkopi_token");
      window.location.href = "/login";
    }
  }
  return res;
}

export async function login(email: string, password: string) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Login failed");
  const data = await res.json();
  localStorage.setItem("kokkopi_token", data.access_token);
  return data;
}

export async function signup(email: string, password: string, tenantName: string) {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, tenant_name: tenantName }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Signup failed");
  const data = await res.json();
  localStorage.setItem("kokkopi_token", data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem("kokkopi_token");
  window.location.href = "/login";
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kokkopi_token");
}

export async function getAgents() {
  const res = await apiFetch("/api/agents");
  if (!res.ok) return [];
  return res.json();
}

export async function createAgent(data: { name: string; website_url: string; sitemap_url?: string; type: string }) {
  const res = await apiFetch("/api/agents", { method: "POST", body: JSON.stringify(data) });
  if (!res.ok) throw new Error((await res.json()).detail || "Failed to create agent");
  return res.json();
}

export async function getAgent(id: string) {
  const res = await apiFetch(`/api/agents/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function deleteAgent(id: string) {
  const res = await apiFetch(`/api/agents/${id}`, { method: "DELETE" });
  return res.ok;
}

export async function getIngestionStatus(agentId: string) {
  const res = await apiFetch(`/api/agents/${agentId}/ingestion/status`);
  if (!res.ok) return null;
  return res.json();
}

export async function startIngestion(agentId: string) {
  const res = await apiFetch(`/api/agents/${agentId}/ingestion/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start ingestion");
  return res.json();
}

export async function getVoiceGallery() {
  const res = await apiFetch("/api/voice/gallery");
  if (!res.ok) return { voices: [] };
  return res.json();
}

export async function getEffectPresets() {
  const res = await apiFetch("/api/voice/effects");
  if (!res.ok) return { presets: [] };
  return res.json();
}

export async function getPronunciation(agentId: string) {
  const res = await apiFetch(`/api/voice/agents/${agentId}/pronunciation`);
  if (!res.ok) return { entries: [] };
  return res.json();
}

export async function updatePronunciation(agentId: string, entries: { term: string; replacement: string }[]) {
  const res = await apiFetch(`/api/voice/agents/${agentId}/pronunciation`, {
    method: "PUT",
    body: JSON.stringify({ entries }),
  });
  if (!res.ok) throw new Error("Failed to update pronunciation");
  return res.json();
}

export async function getProviderCredential() {
  const res = await apiFetch("/api/providers/credential");
  if (!res.ok) return null;
  return res.json();
}

export async function saveProviderCredential(apiKey: string) {
  const res = await apiFetch("/api/providers/credential", {
    method: "POST",
    body: JSON.stringify({ provider: "groq", api_key: apiKey }),
  });
  if (!res.ok) throw new Error("Failed to save API key");
  return res.json();
}

export async function chatWithAgent(agentId: string, message: string, sessionId: string) {
  const res = await fetch(`/api/public/agents/${agentId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  return res;
}

export async function getConversations(agentId: string) {
  const res = await apiFetch(`/api/agents/${agentId}/conversations`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSystemStatus() {
  const res = await apiFetch("/api/voice/system/status");
  if (!res.ok) return null;
  return res.json();
}

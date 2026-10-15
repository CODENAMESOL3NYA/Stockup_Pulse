import { RestockingPlan, PurchaseOrder, TraceEvent, WapeMetrics, AuthUser } from '../types';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const AUTH_TOKEN_KEY = 'stockup-pulse-access-token';

function authenticatedHeaders(json = false): HeadersInit {
  const headers: Record<string, string> = {};
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (json) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function saveAuthToken(token: string) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export async function logoutUser() {
  const headers = authenticatedHeaders();
  localStorage.removeItem(AUTH_TOKEN_KEY);
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers });
  } catch {
    // The local session is cleared even when the API cannot be reached.
  }
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) return await res.json();
    return { status: 'unavailable' };
  } catch {
    return { status: 'unavailable' };
  }
}

export async function fetchTraceEvents(): Promise<{ summary: any; events: TraceEvent[] }> {
  try {
    const res = await fetch(`${API_BASE}/trace`, { headers: authenticatedHeaders() });
    if (res.ok) return await res.json();
  } catch {
    // The API may be offline during local development.
  }
  return { summary: { total_events: 0 }, events: [] };
}

export async function fetchWapeMetrics(): Promise<WapeMetrics | null> {
  try {
    const res = await fetch(`${API_BASE}/metrics`, { headers: authenticatedHeaders() });
    if (res.ok) return await res.json();
  } catch {
    // The API may be offline during local development.
  }
  return null;
}

export async function generatePlan(
  budget: number,
  horizonDays: number,
  items: any[],
  allowSubstitutions = true
): Promise<RestockingPlan> {
  const res = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: authenticatedHeaders(true),
    body: JSON.stringify({
      budget,
      planning_horizon_days: horizonDays,
      items,
      allow_substitutions: allowSubstitutions
    })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Plan request failed: ${res.status}`);
  return data;
}

export async function approvePlan(approved: boolean, planId?: string) {
  const res = await fetch(`${API_BASE}/plan/approve`, {
    method: 'POST',
    headers: authenticatedHeaders(true),
    body: JSON.stringify({ approved, plan_id: planId })
  });
  return await res.json();
}

export async function createPurchaseOrders(approved: boolean, planId?: string): Promise<PurchaseOrder[]> {
  const res = await fetch(`${API_BASE}/orders`, {
    method: 'POST',
    headers: authenticatedHeaders(true),
    body: JSON.stringify({ approved, plan_id: planId, store_name: "Sunnyside Spaza" })
  });

  if (res.status === 409) {
    const errorData = await res.json();
    throw new Error(errorData.error || "HTTP 409: Approval required before creating purchase orders.");
  }

  if (!res.ok) {
    throw new Error(`Failed to create orders: ${res.statusText}`);
  }

  const data = await res.json();
  return data.orders;
}

export async function sendWhatsAppMessage(body: string): Promise<{ reply: string; orders?: PurchaseOrder[] }> {
  const res = await fetch(`${API_BASE}/whatsapp/simulate`, {
    method: 'POST',
    headers: authenticatedHeaders(true),
    body: JSON.stringify({ body })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'WhatsApp simulation failed.');
  return data;
}

export async function fetchCodebaseFiles() {
  try {
    const res = await fetch(`${API_BASE}/codebase`);
    if (res.ok) return await res.json();
  } catch (e) {
    // fallback
  }
  return { files: [] };
}

export async function fetchFileContent(filePath: string) {
  try {
    const res = await fetch(`${API_BASE}/codebase/file?path=${encodeURIComponent(filePath)}`);
    if (res.ok) return await res.json();
  } catch (e) {
    // fallback
  }
  return { content: "" };
}

export async function fetchLiveMarketPrices() {
  try {
    const res = await fetch(`${API_BASE}/market-prices`, { headers: authenticatedHeaders() });
    if (res.ok) return await res.json();
  } catch (e) {
    // The API may be offline during local development.
  }
  return [];
}

export async function syncLiveScraper() {
  try {
    const res = await fetch(`${API_BASE}/scraper/sync`, { method: 'POST', headers: authenticatedHeaders() });
    if (res.ok) return await res.json();
  } catch (e) {
    // The API may be offline during local development.
  }
  return { status: "unavailable", newly_scraped_count: 0, message: "Scraper sync did not complete." };
}

export async function loginUser(whatsappNumber: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ whatsapp_number: whatsappNumber, password })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Authentication failed');
  saveAuthToken(data.access_token);
  return data.user;
}

export async function registerUser(
  fullName: string,
  shopName: string,
  whatsappNumber: string,
  password: string
): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      shop_name: shopName,
      whatsapp_number: whatsappNumber,
      password
    })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Registration failed');
  saveAuthToken(data.access_token);
  return data.user;
}

export async function getSessionUser(): Promise<AuthUser | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authenticatedHeaders() });
    if (res.ok) {
      const data = await res.json();
      return data.user;
    }
  } catch (e) {
    // ignore
  }
  return null;
}


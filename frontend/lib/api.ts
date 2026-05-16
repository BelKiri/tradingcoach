import { createClient } from "@/lib/supabase/client";

const isDev = process.env.NEXT_PUBLIC_API_URL === "http://localhost:8000" ||
  !process.env.NEXT_PUBLIC_API_URL;
const API_BASE = isDev ? "http://localhost:8000" : "/api/proxy";

export interface AccountSummary {
  id: string;
  name: string;
  broker: string | null;
  starting_balance: number | null;
  trades: number;
  pnl: number;
  win_rate: number | null;
}

export interface AccountQuotaFlags {
  id: string;
  upload_used: boolean;
  coaching_used: boolean;
}

export interface UserQuota {
  is_beta_exempt: boolean;
  coaching_sessions_used: number;
  accounts: AccountQuotaFlags[];
}

export async function fetchUserQuota(userId: string): Promise<UserQuota> {
  return apiFetch<UserQuota>(`/api/users/${userId}/quota`);
}

export interface UploadResult {
  trades_parsed: number;
  trades_new: number;
  trades_duplicate: number;
  trades_saved: number;
  errors: string[];
  summary: { total_trades: number; win_rate: number | null; total_pnl: number } | null;
}

export interface BehavioralData {
  revenge_count: number;
  revenge_cost: number;
  martingale_count: number;
  martingale_pnl: number;
  overtrading_days: number;
  overtrading_pnl: number;
  overtrading_wr: number | null;
  averaging_count: number;
  averaging_pnl: number;
  quick_exits_count: number;
  quick_exits_pnl: number;
  sl_with: number;
  sl_without: number;
  no_sl_pnl: number;
}

export interface DashboardData {
  total_trades: number;
  win_rate: number | null;
  total_pnl: number;
  gross_profit: number;
  gross_loss: number;
  profit_factor: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  expectancy: number | null;
  max_drawdown: Record<string, number>;
  equity_curve: Array<{ day: string; label: string; equity: number }>;
  pnl_by_symbol: Record<string, { pnl: number; win_rate: number; trades: number }>;
  pnl_by_session: Record<string, { pnl: number; win_rate: number; trades: number }>;
  pnl_by_day_of_week: Record<string, { pnl: number; win_rate: number; trades: number }>;
  pnl_by_hour: Record<string, { pnl: number; win_rate: number; trades: number }>;
  hold_time: Record<string, unknown> | null;
  streaks: Record<string, unknown>;
  revenge_trades_count: number;
  revenge_trade_cost: number;
  behavioral: BehavioralData;
  risk_per_trade: Array<Record<string, unknown>>;
  trades: Array<Record<string, unknown>>;
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

function handleAuthRedirect(status: number): never | void {
  if (typeof window === "undefined") return;
  if (status === 401) {
    window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
    throw new Error("__auth_redirect__");
  }
  if (status === 403) {
    window.location.href = "/app";
    throw new Error("__auth_redirect__");
  }
}

// ---------------------------------------------------------------------------
// Core fetch
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();

  const mergedHeaders: Record<string, string> = {
    ...authHeaders,
  };

  // Merge existing headers from options
  if (options?.headers) {
    const h = options.headers as Record<string, string>;
    for (const [k, v] of Object.entries(h)) {
      mergedHeaders[k] = v;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: mergedHeaders,
  });

  if (!res.ok) {
    // Silent auth redirects — user never sees error codes
    handleAuthRedirect(res.status);

    const body = await res.text();
    let message = `API error ${res.status}: ${body}`;
    try {
      const json = JSON.parse(body);
      if (json.detail) message = json.detail;
    } catch {
      // body is not JSON, use raw text
    }
    throw new Error(message);
  }
  return res.json();
}

export async function ensureUser(userId: string, email: string | undefined): Promise<void> {
  await apiFetch("/api/users/ensure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, email: email || null }),
  });
}

export async function fetchAccounts(userId: string): Promise<AccountSummary[]> {
  const data = await apiFetch<{ accounts: AccountSummary[] }>(
    `/api/accounts/${userId}`
  );
  return data.accounts;
}

export async function createAccount(
  userId: string,
  name: string,
  startingBalance: number | null,
  broker?: string,
  brokerTimezone?: string,
): Promise<AccountSummary> {
  return apiFetch<AccountSummary>("/api/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      name,
      starting_balance: startingBalance,
      broker: broker || null,
      broker_timezone: brokerTimezone || "UTC+2",
    }),
  });
}

export async function uploadTrades(
  userId: string,
  accountId: string,
  file: File,
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("account_id", accountId);

  return apiFetch<UploadResult>(`/api/upload/${userId}`, {
    method: "POST",
    body: formData,
  });
}

export async function getAccount(accountId: string): Promise<AccountSummary> {
  return apiFetch<AccountSummary>(`/api/accounts/detail/${accountId}`);
}

export async function renameAccount(accountId: string, name: string): Promise<AccountSummary> {
  return apiFetch<AccountSummary>(`/api/accounts/${accountId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function deleteAccount(accountId: string): Promise<void> {
  await apiFetch(`/api/accounts/${accountId}`, { method: "DELETE" });
}

export async function deleteAllUserData(userId: string): Promise<void> {
  await apiFetch(`/api/accounts/user/${userId}/all`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Coaching
// ---------------------------------------------------------------------------

export interface CoachingUsage {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface CoachingResponse {
  session_id: string;
  ai_response: string;
  metrics_snapshot: Record<string, unknown>;
  verdict: string | null;
  created_at: string;
  usage: CoachingUsage;
}

export interface CoachingSession {
  id: string;
  user_id: string;
  account_id: string;
  created_at: string;
  ai_response: string;
  metrics_snapshot: Record<string, unknown> | null;
  recommendations: string[] | null;
  verdict: string | null;
  main_problem: string | null;
  new_trades_count: number | null;
  model_used: string | null;
}

export async function requestCoaching(
  userId: string,
  accountId: string,
): Promise<CoachingResponse> {
  return apiFetch<CoachingResponse>(`/api/coaching/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_id: accountId }),
  });
}

export async function getCoachingSession(
  sessionId: string,
): Promise<CoachingSession> {
  return apiFetch<CoachingSession>(`/api/coaching/session/${sessionId}`);
}

export async function getCoachingSessions(
  userId: string,
  accountId?: string,
): Promise<CoachingSession[]> {
  const params = new URLSearchParams();
  if (accountId) params.set("account_id", accountId);
  const qs = params.toString();
  return apiFetch<CoachingSession[]>(
    `/api/coaching/sessions/${userId}${qs ? `?${qs}` : ""}`,
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function getDashboard(
  userId: string,
  accountId: string,
  dateFrom?: string,
  dateTo?: string,
): Promise<DashboardData> {
  const params = new URLSearchParams({ account_id: accountId });
  if (dateFrom) params.set("since", dateFrom);
  if (dateTo) params.set("until", dateTo);
  return apiFetch<DashboardData>(
    `/api/dashboard/${userId}?${params.toString()}`
  );
}

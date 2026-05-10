import { SWRConfiguration } from "swr";
import { createClient } from "@/lib/supabase/client";

const isDev = process.env.NEXT_PUBLIC_API_URL === "http://localhost:8000" ||
  !process.env.NEXT_PUBLIC_API_URL;
const API_BASE = isDev ? "http://localhost:8000" : "/api/proxy";

/** SWR fetcher — works with absolute API paths like `/api/accounts/...` */
export async function fetcher<T>(path: string): Promise<T> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { headers });

  if (!res.ok) {
    if (typeof window !== "undefined") {
      if (res.status === 401) {
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        throw new Error("__auth_redirect__");
      }
      if (res.status === 403) {
        window.location.href = "/app";
        throw new Error("__auth_redirect__");
      }
    }
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

/** Default SWR config shared across the app. */
export const swrConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  dedupingInterval: 60_000, // 60s — don't refetch same URL within 60s
  errorRetryCount: 2,
};

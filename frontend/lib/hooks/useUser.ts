"use client";

import { useEffect, useRef, useState } from "react";
import { type User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { ensureUser } from "@/lib/api";

export function useUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const ensuredRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const supabase = createClient();

    async function syncUser(u: User | null) {
      if (u && !ensuredRef.current.has(u.id)) {
        ensuredRef.current.add(u.id);
        try {
          await ensureUser(u.id, u.email);
        } catch {
          // non-blocking — user row may already exist
        }
      }
      setUser(u);
      setLoading(false);
    }

    supabase.auth.getUser().then(({ data: { user: u } }) => syncUser(u));

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "TOKEN_REFRESHED" || event === "SIGNED_IN") {
        syncUser(session?.user ?? null);
      } else if (event === "SIGNED_OUT") {
        setUser(null);
        // Quiet redirect to login if on a protected page
        if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) {
          window.location.href = "/login";
        }
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  return { user, loading };
}

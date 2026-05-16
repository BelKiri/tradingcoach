"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useUser } from "@/lib/hooks/useUser";
import { createClient } from "@/lib/supabase/client";
import {
  deleteAccount,
  deleteAllUserData,
  fetchAccounts,
  renameAccount,
  type AccountSummary,
} from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const { user } = useUser();

  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showDeleteAll, setShowDeleteAll] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [busy, setBusy] = useState(false);

  const loadAccounts = useCallback(async () => {
    if (!user) return;
    try {
      const data = await fetchAccounts(user.id);
      setAccounts(data);
    } catch {
      // ignore
    } finally {
      setAccountsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  async function handleRename(accountId: string) {
    if (!editName.trim()) return;
    setBusy(true);
    try {
      await renameAccount(accountId, editName.trim());
      setEditingId(null);
      await loadAccounts();
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteAccount(accountId: string) {
    setBusy(true);
    try {
      await deleteAccount(accountId);
      setDeletingId(null);
      await loadAccounts();
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteAllData() {
    if (!user || deleteConfirmText !== "DELETE") return;
    setBusy(true);
    try {
      await deleteAllUserData(user.id);
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push("/");
      router.refresh();
    } catch {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Profile</CardTitle>
          <CardDescription>Your account information.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Email</label>
            <Input
              value={user?.email || ""}
              readOnly
              className="bg-muted"
            />
          </div>
          <Button size="sm" variant="outline" onClick={handleSignOut}>
            Sign Out
          </Button>
        </CardContent>
      </Card>

      {/* Subscription */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Subscription</CardTitle>
            <Badge variant="secondary">Free Plan</Badge>
          </div>
          <CardDescription>
            Manage your subscription and billing.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-muted/30 p-4">
            <p className="text-sm">
              You&apos;re on the <strong>Free</strong> plan.
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
              <li>{"\u2713"} 1 file upload per account during beta</li>
              <li>{"\u2713"} 1 AI Coach session per account, 3 across the beta</li>
            </ul>
          </div>
          <Button asChild>
            <a href="/#pricing">Upgrade to Pro</a>
          </Button>
        </CardContent>
      </Card>

      {/* Accounts */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Trading Accounts</CardTitle>
          <CardDescription>Manage your connected accounts.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {accountsLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="h-14 animate-pulse rounded-md border bg-muted/20"
                />
              ))}
            </div>
          ) : accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No trading accounts yet.
            </p>
          ) : (
            accounts.map((acct) => (
              <div
                key={acct.id}
                className="flex items-center justify-between rounded-md border px-4 py-3"
              >
                <div className="flex-1 min-w-0">
                  {editingId === acct.id ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-8 text-sm"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRename(acct.id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        autoFocus
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => handleRename(acct.id)}
                      >
                        Save
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm font-medium">{acct.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {acct.trades} trades
                      </p>
                    </>
                  )}
                </div>

                {editingId !== acct.id && (
                  <div className="flex gap-1 ml-2">
                    {deletingId === acct.id ? (
                      <>
                        <span className="text-xs text-red-400 mr-2 self-center">
                          Delete this account?
                        </span>
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={busy}
                          onClick={() => handleDeleteAccount(acct.id)}
                        >
                          Confirm
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingId(null)}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingId(acct.id);
                            setEditName(acct.name);
                          }}
                        >
                          Rename
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300"
                          onClick={() => setDeletingId(acct.id)}
                        >
                          Delete
                        </Button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-red-500/20">
        <CardHeader>
          <CardTitle className="text-lg text-red-400">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible actions. Be careful.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Delete all data</p>
              <p className="text-xs text-muted-foreground">
                Remove all trades, accounts, and coaching history.
              </p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDeleteAll(true)}
            >
              Delete All Data
            </Button>
          </div>

          {showDeleteAll && (
            <div className="rounded-md border border-red-500/30 bg-red-500/5 p-4 space-y-3">
              <p className="text-sm text-red-400">
                This will permanently delete all your accounts, trades, and coaching sessions. This action cannot be undone.
              </p>
              <p className="text-sm text-muted-foreground">
                Type <strong>DELETE</strong> to confirm:
              </p>
              <div className="flex gap-2">
                <Input
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder="Type DELETE"
                  className="h-8 max-w-[200px]"
                />
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deleteConfirmText !== "DELETE" || busy}
                  onClick={handleDeleteAllData}
                >
                  {busy ? "Deleting..." : "Confirm Delete"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowDeleteAll(false);
                    setDeleteConfirmText("");
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

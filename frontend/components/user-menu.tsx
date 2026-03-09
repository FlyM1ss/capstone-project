"use client";

import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const { user, loading, logout } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <a href="/login">
        <Button variant="outline" size="sm">
          Sign in
        </Button>
      </a>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">
        {user.email}{" "}
        <span className="rounded-full border px-2 py-0.5 text-xs">
          {user.role}
        </span>
      </span>
      <Button variant="outline" size="sm" onClick={logout}>
        Sign out
      </Button>
    </div>
  );
}

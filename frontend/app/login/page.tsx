"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { useLogin } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  // Self-route: if no user exists yet, go to the setup wizard.
  useEffect(() => {
    api
      .status()
      .then((s) => {
        if (s.setup_required) router.replace("/setup");
        else setChecking(false);
      })
      .catch(() => setChecking(false));
  }, [router]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    login.mutate(
      { username: username.trim(), password },
      {
        onError: (err) => {
          setError(err instanceof ApiError ? err.message : "登录失败");
        },
      },
    );
  };

  if (checking) return <div className="p-8 text-muted">加载中…</div>;

  return (
    <main className="min-h-dvh flex items-center justify-center p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-surface p-6"
      >
        <h1 className="text-xl font-semibold">登录</h1>
        <div className="space-y-1">
          <label htmlFor="u" className="text-sm">用户名</label>
          <Input
            id="u"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="p" className="text-sm">密码</label>
          <Input
            id="p"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        {error && <p role="alert" className="text-sm text-explicit">{error}</p>}
        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? "登录中…" : "登录"}
        </Button>
      </form>
    </main>
  );
}

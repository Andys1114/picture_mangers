"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/common/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
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
    <AuthCard title="登录" description="输入你的账户信息以进入图库。">
      <form onSubmit={onSubmit} className="space-y-4">
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
          <PasswordInput
            id="p"
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
    </AuthCard>
  );
}

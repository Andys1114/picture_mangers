"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/common/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { api, ApiError } from "@/lib/api";
import { useSetup } from "@/hooks/useAuth";

export default function SetupPage() {
  const router = useRouter();
  const setup = useSetup();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  // Self-route: if a user already exists, /setup is closed.
  useEffect(() => {
    api
      .status()
      .then((s) => {
        if (!s.setup_required) router.replace("/login");
        else setChecking(false);
      })
      .catch(() => setChecking(false));
  }, [router]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setup.mutate(
      { username: username.trim(), password },
      {
        onError: (err) => {
          setError(err instanceof ApiError ? err.message : "创建失败");
        },
      },
    );
  };

  if (checking) return <div className="p-8 text-muted">加载中…</div>;

  return (
    <AuthCard title="首次启动" description="创建你的管理员账户（仅此一条）。">
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
          <label htmlFor="p" className="text-sm">
            密码
            <span className="text-muted ml-1 text-xs">至少 8 位</span>
          </label>
          <PasswordInput
            id="p"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        {error && (
          <p role="alert" className="text-sm text-explicit">{error}</p>
        )}
        <Button type="submit" className="w-full" disabled={setup.isPending}>
          {setup.isPending ? "创建中…" : "创建并登录"}
        </Button>
      </form>
    </AuthCard>
  );
}

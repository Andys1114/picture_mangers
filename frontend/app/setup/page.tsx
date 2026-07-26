"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/common/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useSetup } from "@/hooks/useAuth";

export default function SetupPage() {
  const router = useRouter();
  const setup = useSetup();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Only the password has client-side validation; server/network errors are
  // form-level and must not mark fields invalid.
  const [pwInvalid, setPwInvalid] = useState(false);
  const [checking, setChecking] = useState(true);
  const passwordRef = useRef<HTMLInputElement>(null);

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
    setPwInvalid(false);
    if (password.length < 8) {
      setError("密码至少 8 位");
      setPwInvalid(true);
      passwordRef.current?.focus();
      return;
    }
    setup.mutate(
      { username: username.trim(), password },
      {
        onError: (err) => {
          setError(
            err instanceof ApiError ? err.message : "无法连接服务器，请确认后端已启动后重试",
          );
        },
      },
    );
  };

  if (checking) {
    return (
      <AuthCard title="首次启动" description="创建你的管理员账户（仅此一条）。">
        <div role="status" aria-label="加载中" className="space-y-4">
          <div className="space-y-1">
            <Skeleton className="h-5 w-12" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-1">
            <Skeleton className="h-5 w-12" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-10 w-full" />
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="首次启动" description="创建你的管理员账户（仅此一条）。">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="u" className="text-sm font-medium">用户名</label>
          <Input
            id="u"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="p" className="text-sm font-medium">
            密码
            <span className="text-muted ml-1 text-xs font-normal">至少 8 位</span>
          </label>
          <PasswordInput
            id="p"
            ref={passwordRef}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            aria-invalid={pwInvalid}
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

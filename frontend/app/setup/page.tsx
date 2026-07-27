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

const FOOTER = "拥有者账户只在首次启动时创建一次，之后用它登录。";

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
      <AuthCard title="首次启动" description="创建你的拥有者账户（仅此一条）。" footer={FOOTER}>
        <div role="status" aria-label="加载中" className="space-y-[15px]">
          <div className="space-y-1.5">
            <Skeleton className="h-5 w-12" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-1.5">
            <Skeleton className="h-5 w-12" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-[42px] w-full" />
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="首次启动" description="创建你的拥有者账户（仅此一条）。" footer={FOOTER}>
      <form onSubmit={onSubmit} className="space-y-[15px]">
        <div className="space-y-1.5">
          <label htmlFor="u" className="text-[12.5px] font-medium text-secondary">
            用户名
          </label>
          <Input
            id="u"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="p" className="text-[12.5px] font-medium text-secondary">
            密码
            <span className="ml-1 text-xs font-normal text-muted">至少 8 位</span>
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
        <Button type="submit" size="lg" className="mt-1 w-full" disabled={setup.isPending}>
          {setup.isPending ? "创建中…" : "创建并登录"}
        </Button>
      </form>
    </AuthCard>
  );
}

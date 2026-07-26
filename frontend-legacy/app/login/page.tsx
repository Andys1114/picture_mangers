"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/common/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useLogin } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Credential rejections mark the fields; network failures are form-level only.
  const [credentialError, setCredentialError] = useState(false);
  const [checking, setChecking] = useState(true);
  const usernameRef = useRef<HTMLInputElement>(null);

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
    setCredentialError(false);
    login.mutate(
      { username: username.trim(), password },
      {
        onError: (err) => {
          const isApi = err instanceof ApiError;
          setError(isApi ? err.message : "无法连接服务器，请确认后端已启动后重试");
          setCredentialError(isApi);
          usernameRef.current?.focus();
        },
      },
    );
  };

  if (checking) {
    return (
      <AuthCard title="登录" description="输入你的账户信息以进入图库。">
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
    <AuthCard title="登录" description="输入你的账户信息以进入图库。">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="u" className="text-sm font-medium">用户名</label>
          <Input
            id="u"
            ref={usernameRef}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            aria-invalid={credentialError}
            required
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="p" className="text-sm font-medium">密码</label>
          <PasswordInput
            id="p"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            aria-invalid={credentialError}
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

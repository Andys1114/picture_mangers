import type { NextConfig } from "next";

const API_TARGET = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Same-origin proxy to the FastAPI backend so the browser's HttpOnly session
  // cookie travels automatically and we never hardcode backend URLs in client
  // code. /api/* and /media/* are rewritten to the backend origin.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_TARGET}/api/:path*` },
      { source: "/media/:path*", destination: `${API_TARGET}/media/:path*` },
    ];
  },
};

export default nextConfig;

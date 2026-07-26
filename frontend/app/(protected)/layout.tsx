export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  // Auth shell: the cookie gate lives in middleware.ts and the /me 401 redirect
  // in app/providers.tsx (MeGate). This layout is the mount point for the
  // browse chrome (topbar / filter rail), which lands in later stages.
  return <>{children}</>;
}

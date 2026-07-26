import { Suspense } from "react";
import { Topbar } from "@/components/browse/topbar";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  // pt-14 clears the fixed 56px topbar.
  return (
    <div className="pt-14">
      <Suspense fallback={null}>
        <Topbar />
      </Suspense>
      {children}
    </div>
  );
}

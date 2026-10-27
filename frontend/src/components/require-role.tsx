"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";

import { Loading } from "@/components/page-state";
import { useAuth } from "@/components/providers";
import { Alert } from "@/components/ui/alert";
import type { Role } from "@/lib/types";

/**
 * Usability guard only. Every API call remains authorized by FastAPI.
 */
export function RequireRole({
  roles,
  children,
}: {
  roles: Role[];
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Loading label="Redirecting to sign in…" />;
  if (!roles.includes(user.role)) {
    return (
      <Alert variant="error" title="Access not permitted">
        This area is not available to your account. Sign in with a different role to continue.
      </Alert>
    );
  }
  return <>{children}</>;
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/providers";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const CUSTOMER_LINKS = [
  { href: "/", label: "Providers" },
  { href: "/dashboard", label: "My appointments" },
];

const PROVIDER_LINKS = [
  { href: "/provider", label: "Dashboard" },
  { href: "/provider/services", label: "Services" },
  { href: "/provider/availability", label: "Availability" },
];

const ADMIN_LINKS = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/appointments", label: "Appointments" },
];

export function SiteHeader() {
  const { user, loading, signOut } = useAuth();
  const pathname = usePathname();

  const links =
    user?.role === "PROVIDER"
      ? PROVIDER_LINKS
      : user?.role === "ADMIN"
        ? ADMIN_LINKS
        : CUSTOMER_LINKS;

  return (
    <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
      <div className="page-container flex h-16 items-center justify-between gap-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Appointly
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium hover:bg-accent",
                pathname === link.href ? "bg-accent" : "text-muted-foreground",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {loading ? (
            <span className="text-sm text-muted-foreground">Loading…</span>
          ) : user ? (
            <>
              <span className="hidden text-sm text-muted-foreground md:inline">
                {user.full_name}
              </span>
              <Button variant="outline" size="sm" onClick={() => void signOut()}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link href="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                Sign in
              </Link>
              <Link href="/register" className={buttonVariants({ variant: "default", size: "sm" })}>
                Register
              </Link>
            </>
          )}
        </div>
      </div>
      <nav className="flex items-center gap-1 overflow-x-auto border-t px-4 py-2 sm:hidden">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium hover:bg-accent",
              pathname === link.href ? "bg-accent" : "text-muted-foreground",
            )}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}

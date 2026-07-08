"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { contentContainerClassName } from "@/lib/ui";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/compatibility", label: "Compatibility" },
  { href: "/preferences", label: "Preferences" },
  { href: "/analytics", label: "Analytics" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav
      className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/95 backdrop-blur"
      aria-label="Main"
    >
      <div
        className={`${contentContainerClassName} flex items-center gap-4 py-3 sm:gap-6 sm:py-3.5`}
      >
        <Link
          href="/"
          className="shrink-0 text-sm font-semibold tracking-tight text-slate-900"
        >
          BookLens
        </Link>

        <div className="-mx-4 min-w-0 flex-1 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <ul className="flex gap-1 sm:justify-end">
            {navItems.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href} className="shrink-0">
                  <Link
                    href={item.href}
                    className={`block rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-teal-700 text-white"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                    aria-current={active ? "page" : undefined}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </nav>
  );
}

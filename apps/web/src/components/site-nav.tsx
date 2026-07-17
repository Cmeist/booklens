"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { contentContainerClassName } from "@/lib/ui";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Discover" },
  { href: "/compatibility", label: "For You" },
  { href: "/profile", label: "My Library" },
  { href: "/analytics", label: "Insights" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuPanelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    }

    function handlePointerDown(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !menuPanelRef.current?.contains(event.target) &&
        !menuButtonRef.current?.contains(event.target)
      ) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [menuOpen]);

  return (
    <nav
      className="sticky top-0 z-20 border-b border-rule bg-paper-raised/95 backdrop-blur"
      aria-label="Main"
    >
      <div
        className={`${contentContainerClassName} flex items-center gap-4 py-2.5 sm:gap-6 sm:py-3`}
      >
        <Link
          href="/"
          className="group flex shrink-0 items-center gap-2.5 text-ink"
        >
          <span className="bookplate-mark" aria-hidden="true">B</span>
          <span>
            <span className="block font-display text-xl font-semibold leading-none tracking-tight">
              BookLens
            </span>
            <span className="mt-0.5 hidden text-[9px] font-semibold uppercase tracking-[0.2em] text-walnut sm:block">
              The reading room
            </span>
          </span>
        </Link>

        <div className="hidden min-w-0 flex-1 md:block">
          <ul className="flex justify-end gap-1">
            {navItems.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href} className="shrink-0">
                  <Link
                    href={item.href}
                    className={`block rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-forest text-white shadow-sm"
                        : "text-ink-soft hover:bg-paper-deep hover:text-ink"
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

        <button
          ref={menuButtonRef}
          type="button"
          className="ml-auto inline-flex items-center gap-2 rounded-full border border-rule bg-paper px-3 py-2 text-xs font-semibold text-ink md:hidden"
          aria-expanded={menuOpen}
          aria-controls="mobile-main-navigation"
          onClick={() => setMenuOpen((current) => !current)}
        >
          Menu
          <span aria-hidden="true" className="text-walnut">
            {menuOpen ? "×" : "☰"}
          </span>
        </button>
      </div>

      {menuOpen ? (
        <div
          ref={menuPanelRef}
          id="mobile-main-navigation"
          className="absolute inset-x-0 top-full border-b border-rule bg-paper-raised p-3 shadow-[0_18px_35px_rgba(61,46,28,0.14)] md:hidden"
        >
          <ul className="mx-auto grid max-w-7xl gap-1">
            {navItems.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className={`block rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
                      active
                        ? "bg-forest text-white"
                        : "text-ink-soft hover:bg-paper-deep hover:text-ink"
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
      ) : null}
    </nav>
  );
}

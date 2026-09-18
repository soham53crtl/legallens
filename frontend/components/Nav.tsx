"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useDoc } from "@/lib/store";
import UploadModal from "./UploadModal";

const TABS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analysis", label: "Analysis" },
  { href: "/chat", label: "Ask" },
  { href: "/compare", label: "Compare" },
  { href: "/lawyer-prep", label: "Lawyer Prep" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { doc, resetAll } = useDoc();
  const [modalOpen, setModalOpen] = useState(false);

  const isLanding = pathname === "/";

  return (
    <>
      <nav className="sticky top-0 z-40 flex items-center justify-between px-7 py-3.5 border-b border-line bg-paper/90 backdrop-blur-sm">
        <Link href="/" className="flex items-center gap-2 select-none" onClick={() => !doc && undefined}>
          <div className="w-[26px] h-[26px] border-[1.6px] border-ink rounded-sm relative flex-shrink-0">
            <span className="absolute left-[5px] right-[5px] top-[6px] h-[2px] bg-highlight" />
            <span className="absolute left-[5px] right-[9px] top-[11px] h-[2px] bg-ink/55" />
          </div>
          <span className="font-serif text-[19px] font-semibold tracking-tight">LegalLens</span>
        </Link>

        {doc && !isLanding && (
          <div className="hidden md:flex gap-0.5 items-center">
            {TABS.map((t) => (
              <Link
                key={t.href}
                href={t.href}
                aria-current={pathname === t.href ? "page" : undefined}
                className={`px-3.5 py-2 text-[13.5px] font-medium border-b-2 ${
                  pathname === t.href
                    ? "text-ink border-highlight"
                    : "text-ink-soft border-transparent hover:text-ink"
                }`}
              >
                {t.label}
              </Link>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2.5">
          {doc ? (
            <button
              className="px-3.5 py-2 rounded text-[12.5px] font-semibold border border-line-strong hover:bg-paper-alt"
              onClick={() => {
                resetAll();
                router.push("/");
              }}
            >
              New document
            </button>
          ) : (
            <button
              className="px-3.5 py-2 rounded text-[12.5px] font-semibold border border-line-strong hover:bg-paper-alt"
              onClick={() => setModalOpen(true)}
            >
              Upload document
            </button>
          )}
        </div>
      </nav>
      {modalOpen && <UploadModal mode="primary" onClose={() => setModalOpen(false)} />}
    </>
  );
}

"use client";
import { useState } from "react";
import UploadModal from "@/components/UploadModal";

export default function Landing() {
  const [modal, setModal] = useState<"primary" | "compare" | null>(null);

  return (
    <div>
      <div className="grid md:grid-cols-[1.1fr_1fr] gap-14 items-center pt-9 md:pt-16 pb-12">
        <div>
          <div className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-soft border border-line-strong px-2.5 py-1 rounded-full mb-5">
            <span className="text-highlight text-[9px]">●</span> AI for Legal Assistance &amp; Access
          </div>
          <h1 className="font-serif text-[34px] md:text-[46px] leading-[1.08] font-medium mb-5 tracking-tight">
            Understand the fine print.
            <br />
            Know what to{" "}
            <em
              className="not-italic font-medium text-highlight-ink"
              style={{ backgroundImage: "linear-gradient(transparent 62%, #F6E1B4 0%)" }}
            >
              <i>ask</i>
            </em>
            .
          </h1>
          <p className="text-[16.5px] text-ink-soft max-w-[460px] mb-7">
            Upload any lease, offer letter, contract or policy. LegalLens explains it in plain
            language, flags what deserves your attention, and helps you prepare for the
            conversation that follows.
          </p>
          <div className="flex gap-3 flex-wrap">
            <button
              className="px-4 py-2.5 rounded text-[13.5px] font-semibold bg-ink text-paper hover:opacity-80"
              onClick={() => setModal("primary")}
            >
              Upload a document
            </button>
            <button
              className="px-4 py-2.5 rounded text-[13.5px] font-semibold border border-line-strong hover:bg-paper-alt"
              onClick={() => setModal("primary")}
            >
              Try the sample lease
            </button>
            <button
              className="px-4 py-2.5 rounded text-[13.5px] font-semibold border border-line-strong hover:bg-paper-alt"
              onClick={() => setModal("compare")}
            >
              Compare documents
            </button>
          </div>
          <div className="mt-3.5 text-[12.5px] text-ink-faint">
            PDF, DOCX or TXT · processed for this session, never shared
          </div>
        </div>

        <div className="relative max-w-[400px] mx-auto hidden md:block">
          <div className="bg-white border border-line-strong rounded-sm px-7 py-8 shadow-paper rotate-1">
            <div className="h-3 w-[55%] bg-ink/85 rounded-sm mb-5" />
            {[100, 100, 60].map((w, i) => (
              <div key={i} className="h-2 bg-paper-deep rounded-sm mb-2.5" style={{ width: `${w}%` }} />
            ))}
            <div className="h-2 bg-highlight-soft rounded-sm mb-2.5 mt-4" style={{ width: "100%" }} />
            <div className="h-2 bg-paper-deep rounded-sm mb-2.5" style={{ width: "100%" }} />
            <div className="h-2 bg-paper-deep rounded-sm mb-2.5" style={{ width: "60%" }} />
            <div className="h-2 bg-highlight-soft rounded-sm mb-2.5 mt-4" style={{ width: "100%" }} />
            <div className="h-2 bg-paper-deep rounded-sm" style={{ width: "60%" }} />
          </div>
          <div className="absolute -right-10 top-[118px] w-[190px] bg-ink text-paper text-[11.5px] px-3 py-2.5 rounded-sm leading-snug shadow-paper -rotate-2">
            <div className="text-[9px] tracking-wider text-highlight font-semibold mb-0.5">
              NOTICE PERIOD
            </div>
            60 days written notice required before termination — see Clause 9.
          </div>
          <div className="absolute -left-8 top-[210px] bg-risk-high-bg text-risk-high text-[11px] font-semibold px-2.5 py-1.5 rounded-full shadow-paper">
            🔴 Auto-renewal clause
          </div>
        </div>
      </div>

      <div className="pt-9 pb-14 border-t border-line">
        <h2 className="text-[14px] font-semibold text-ink-soft mb-6">How it works</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-y-6">
          {[
            ["01", "Upload", "Drop in a PDF, Word file or plain text. LegalLens reads it clause by clause."],
            ["02", "Understand", "Get a plain-language summary, your obligations, rights and key dates."],
            ["03", "Investigate", "See flagged risks, compare versions, and ask the document direct questions."],
            ["04", "Prepare", "Generate a briefing sheet to bring to a qualified legal professional."],
          ].map(([num, title, body], i, arr) => (
            <div key={num} className={`pr-5 ${i < arr.length - 1 ? "md:border-r border-b md:border-b-0 border-line pb-5 md:pb-0" : ""}`}>
              <div className="font-mono text-[12px] text-highlight-ink mb-2.5">{num}</div>
              <h3 className="text-[16.5px] font-semibold mb-2">{title}</h3>
              <p className="text-[13px] text-ink-soft">{body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-paper-alt border border-line rounded-md px-5 py-4 text-[12.5px] text-ink-soft mb-14">
        <strong className="text-ink">
          LegalLens provides general legal information and document assistance.
        </strong>{" "}
        It does not provide legal advice and does not replace a qualified legal professional. Your
        documents stay isolated to your session and are not shared with other users.
      </div>

      {modal && <UploadModal mode={modal} onClose={() => setModal(null)} />}
    </div>
  );
}

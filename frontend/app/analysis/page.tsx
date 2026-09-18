"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useDoc } from "@/lib/store";
import type { Severity } from "@/lib/types";

const SEV_ICON: Record<Severity, string> = { high: "🔴", medium: "🟠", standard: "🟢" };
const SEV_LABEL: Record<Severity, string> = { high: "High priority", medium: "Needs attention", standard: "Standard" };

export default function Analysis() {
  const router = useRouter();
  const { doc } = useDoc();
  const [filter, setFilter] = useState<"all" | Severity>("all");
  const [quoteId, setQuoteId] = useState<string | null>(null);

  useEffect(() => {
    if (!doc) router.replace("/");
  }, [doc, router]);

  const clauseMap = useMemo(() => {
    const m = new Map<string, string>();
    doc?.clauses.forEach((c) => m.set(c.id, c.text));
    return m;
  }, [doc]);

  if (!doc) return null;
  const a = doc.summary;
  const risks = doc.risks || [];
  const filtered = filter === "all" ? risks : risks.filter((r) => r.severity === filter);

  if (doc.analysisStatus !== "done" || !a) {
    return (
      <div className="py-16 text-center text-ink-faint">
        {doc.analysisStatus === "error" ? doc.analysisError : "Analysis is still running — head to the Dashboard, or wait a moment."}
      </div>
    );
  }

  const col = (title: string, items: string[]) => (
    <div key={title}>
      <h4 className="text-[13px] font-semibold mb-2.5">{title}</h4>
      <ul className="list-disc pl-[18px] marker:text-highlight-ink">
        {items.length ? (
          items.map((i, idx) => (
            <li key={idx} className="text-[13.5px] mb-1.5 text-ink-soft">
              {i}
            </li>
          ))
        ) : (
          <li className="text-[13.5px] text-ink-faint">None identified</li>
        )}
      </ul>
    </div>
  );

  return (
    <div>
      <div className="pt-6 pb-1">
        <h2 className="text-[26px] font-medium mb-1">What am I agreeing to?</h2>
        <p className="text-ink-soft text-[13.5px]">
          A plain-language breakdown of the document&apos;s key terms, grounded in the text you uploaded.
        </p>
      </div>

      <section className="max-w-[720px] py-7 border-t border-line">
        <SectionLabel>Plain-language summary</SectionLabel>
        <p className="font-serif text-[17px] leading-[1.65]">{a.summary}</p>
      </section>

      <section className="max-w-[720px] py-7 border-t border-line">
        <SectionLabel>Your obligations, rights &amp; terms</SectionLabel>
        <div className="grid md:grid-cols-2 gap-6">
          {col("Your obligations", a.obligations)}
          {col("Your rights", a.rights)}
          {col("Payments & fees", a.payments)}
          {col("Restrictions", a.restrictions)}
          {col("Termination conditions", a.terminationConditions)}
          {col("Potential consequences", a.consequences)}
          {a.missingOrInconsistent.length > 0 && (
            <div className="md:col-span-2">
              <h4 className="text-[13px] font-semibold mb-2.5">Missing or inconsistent information</h4>
              <ul className="list-disc pl-[18px]">
                {a.missingOrInconsistent.map((i, idx) => (
                  <li key={idx} className="text-[13.5px] mb-1.5 text-ink-soft">
                    {i}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="max-w-[720px] py-7 border-t border-line">
        <SectionLabel>Important dates &amp; deadlines</SectionLabel>
        {a.importantDates.length ? (
          a.importantDates.map((d, i) => (
            <div key={i} className="flex gap-4 py-3.5 border-b border-line last:border-0">
              <div className="font-mono text-[12.5px] text-highlight-ink w-[120px] flex-shrink-0 pt-0.5">
                {d.label}
              </div>
              <div>
                <div className="font-semibold text-[13.5px] mb-0.5">{d.detail}</div>
                {d.clauseId && <ClauseRef id={d.clauseId} onClick={setQuoteId} />}
              </div>
            </div>
          ))
        ) : (
          <p className="text-ink-faint text-[13px]">No explicit dates or deadlines were detected in this document.</p>
        )}
      </section>

      <section className="py-7 border-t border-line">
        <SectionLabel>Risk &amp; clause scanner</SectionLabel>
        <div className="flex gap-2 mb-4.5 flex-wrap">
          {(["all", "high", "medium", "standard"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              aria-pressed={filter === s}
              className={`text-[12.5px] px-3.5 py-1.5 rounded-full border ${
                filter === s ? "bg-ink text-paper border-ink" : "bg-white text-ink-soft border-line-strong"
              }`}
            >
              {s === "all" ? "All" : `${SEV_ICON[s]} ${SEV_LABEL[s]}`}
            </button>
          ))}
        </div>
        <div className="max-w-[720px]">
          {filtered.length ? (
            filtered.map((r, i) => (
              <div
                key={i}
                className="border border-line rounded-sm p-4 mb-2.5"
                style={{
                  borderLeftWidth: 4,
                  borderLeftColor:
                    r.severity === "high" ? "#AE3A2C" : r.severity === "medium" ? "#B9781C" : "#3E6E52",
                }}
              >
                <div className="flex justify-between items-center gap-2.5 mb-1.5">
                  <span className="font-semibold text-[14px]">
                    {SEV_ICON[r.severity]} {r.title}
                  </span>
                  <span
                    className={`text-[10.5px] font-bold uppercase tracking-wide px-2.5 py-0.5 rounded-full flex-shrink-0 ${
                      r.severity === "high"
                        ? "bg-risk-high-bg text-risk-high"
                        : r.severity === "medium"
                        ? "bg-risk-med-bg text-risk-med"
                        : "bg-risk-low-bg text-risk-low"
                    }`}
                  >
                    {SEV_LABEL[r.severity]}
                  </span>
                </div>
                <div className="text-[11px] text-ink-faint font-mono mb-1.5">{r.category}</div>
                <p className="text-[13.5px] text-ink-soft">{r.explanation}</p>
                {r.clauseId && (
                  <div className="mt-2">
                    <ClauseRef id={r.clauseId} onClick={setQuoteId} label={`${r.clauseId} — view clause`} />
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-ink-faint text-[13px]">No items in this category.</p>
          )}
        </div>
      </section>

      {quoteId && clauseMap.has(quoteId) && (
        <div className="max-w-[720px] bg-paper-alt border border-line rounded-md p-4.5 my-4">
          <div className="font-mono text-[11px] text-ink-faint mb-1.5">{quoteId} — source text</div>
          <p className="whitespace-pre-wrap text-[13px]">{clauseMap.get(quoteId)}</p>
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[13px] uppercase tracking-wider text-ink-faint font-semibold mb-4">{children}</h3>
  );
}
function ClauseRef({ id, onClick, label }: { id: string; onClick: (id: string) => void; label?: string }) {
  return (
    <button
      type="button"
      onClick={() => onClick(id)}
      className="inline-block text-[11px] font-mono bg-paper-alt border border-line px-1.5 py-0.5 rounded-sm cursor-pointer text-ink-soft hover:bg-highlight-soft hover:border-highlight focus-visible:outline focus-visible:outline-2 focus-visible:outline-highlight"
      aria-label={label ? undefined : `View source text for clause ${id}`}
    >
      {label || id}
    </button>
  );
}

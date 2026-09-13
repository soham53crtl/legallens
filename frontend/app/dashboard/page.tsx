"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useDoc } from "@/lib/store";
import { fetchSummary, fetchRisks, ApiError } from "@/lib/api";

export default function Dashboard() {
  const router = useRouter();
  const { sessionId, doc, updateDoc } = useDoc();

  useEffect(() => {
    if (!doc) {
      router.replace("/");
      return;
    }
    if (doc.analysisStatus !== "idle" || !sessionId) return;
    updateDoc({ analysisStatus: "loading" });
    Promise.all([
      fetchSummary(sessionId, doc.doc_id),
      fetchRisks(sessionId, doc.doc_id),
    ])
      .then(([summary, riskRes]) => {
        updateDoc({ summary, risks: riskRes.risks, analysisStatus: "done" });
      })
      .catch((e) => {
        const msg = e instanceof ApiError ? e.message : "Analysis failed.";
        updateDoc({ analysisStatus: "error", analysisError: msg });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.doc_id, sessionId]);

  if (!doc) return null;

  const counts = { high: 0, medium: 0, standard: 0 };
  (doc.risks || []).forEach((r) => {
    if (r.severity in counts) counts[r.severity]++;
  });

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2.5 pt-6 pb-1.5">
        <div>
          <div className="font-serif text-[22px] font-semibold">{doc.name}</div>
          <div className="text-[12.5px] text-ink-faint mt-0.5">
            {doc.word_count} words · {doc.clauses.length} clauses detected
          </div>
        </div>
        <StatusPill status={doc.analysisStatus} error={doc.analysisError} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3.5 py-5 pb-14">
        {/* Summary card */}
        <Card className="md:col-span-2">
          <CardHead title="Document Summary" tag={(doc.summary?.documentType || "SUMMARY").toUpperCase()} />
          {doc.analysisStatus === "loading" || doc.analysisStatus === "idle" ? (
            <SkeletonLines />
          ) : doc.analysisStatus === "error" ? (
            <p className="text-risk-high text-[13px]">{doc.analysisError}</p>
          ) : (
            <>
              <p className="text-ink-soft text-[13px]">{doc.summary?.summary}</p>
              <CardCta href="/analysis">View full analysis</CardCta>
            </>
          )}
        </Card>

        {/* Risk card */}
        <Card>
          <CardHead title="Risk Scanner" tag="RISK" />
          {doc.analysisStatus === "done" ? (
            <>
              <div className="flex gap-2 mt-0.5">
                <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-risk-high-bg text-risk-high">
                  🔴 {counts.high}
                </span>
                <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-risk-med-bg text-risk-med">
                  🟠 {counts.medium}
                </span>
                <span className="text-[12px] font-semibold px-2.5 py-1 rounded-full bg-risk-low-bg text-risk-low">
                  🟢 {counts.standard}
                </span>
              </div>
              <CardCta href="/analysis">View flagged clauses</CardCta>
            </>
          ) : (
            <SkeletonLines n={1} />
          )}
        </Card>

        {/* Dates card */}
        <Card>
          <CardHead title="Important Dates" tag="DATES" />
          {doc.analysisStatus === "done" ? (
            <>
              {(doc.summary?.importantDates || []).slice(0, 3).map((d, i) => (
                <div key={i} className="flex justify-between gap-2 text-[12.5px] py-1 border-b border-dashed border-line last:border-0">
                  <span>{d.label}</span>
                  <span className="text-ink-soft">{d.detail}</span>
                </div>
              ))}
              {(doc.summary?.importantDates || []).length === 0 && (
                <p className="text-ink-faint text-[13px]">No explicit dates detected.</p>
              )}
              <CardCta href="/analysis">Full timeline</CardCta>
            </>
          ) : (
            <SkeletonLines n={1} />
          )}
        </Card>

        {/* Terms card */}
        <Card>
          <CardHead title="Rights & Obligations" tag="TERMS" />
          {doc.analysisStatus === "done" ? (
            <>
              <p className="text-ink-soft text-[13px]">
                {(doc.summary?.obligations || []).length} obligations ·{" "}
                {(doc.summary?.rights || []).length} rights identified
              </p>
              <CardCta href="/analysis">See details</CardCta>
            </>
          ) : (
            <SkeletonLines n={1} />
          )}
        </Card>

        <Card>
          <CardHead title="Ask Your Document" tag="CHAT" />
          <p className="text-ink-soft text-[13px]">
            Ask direct questions and get answers grounded in the text, with clause citations.
          </p>
          <CardCta href="/chat">Open chat</CardCta>
        </Card>

        <Card>
          <CardHead title="Compare Contracts" tag="DIFF" />
          <p className="text-ink-soft text-[13px]">Upload a second version to see what changed.</p>
          <CardCta href="/compare">Compare documents</CardCta>
        </Card>

        <Card>
          <CardHead title="Lawyer Prep" tag="BRIEF" />
          <p className="text-ink-soft text-[13px]">Generate a shareable briefing for a legal professional.</p>
          <CardCta href="/lawyer-prep">Prepare briefing</CardCta>
        </Card>
      </div>
    </div>
  );
}

function StatusPill({ status, error }: { status: string; error?: string }) {
  if (status === "done")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full bg-paper-alt border border-line text-ink-soft">
        <span className="text-risk-low">✓</span> Analysis complete
      </span>
    );
  if (status === "error")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full bg-risk-high-bg border border-line text-risk-high">
        Analysis failed{error ? ` — ${error}` : ""}
      </span>
    );
  return (
    <span className="status-dot inline-flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full bg-paper-alt border border-line text-ink-soft">
      Analyzing document…
    </span>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white border border-line rounded-sm p-5 flex flex-col gap-2.5 ${className}`}>
      {children}
    </div>
  );
}
function CardHead({ title, tag }: { title: string; tag: string }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      <span className="text-[10.5px] font-mono text-ink-faint">{tag}</span>
    </div>
  );
}
function CardCta({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="mt-auto text-[12.5px] font-semibold text-highlight-ink self-start">
      {children} →
    </Link>
  );
}
function SkeletonLines({ n = 3 }: { n?: number }) {
  const widths = ["95%", "80%", "60%"];
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="skeleton" style={{ width: widths[i % 3] }} />
      ))}
    </div>
  );
}

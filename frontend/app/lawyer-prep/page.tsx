"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoc } from "@/lib/store";
import { generateLawyerPrep, ApiError } from "@/lib/api";
import type { LawyerPrepResult } from "@/lib/types";

export default function LawyerPrep() {
  const router = useRouter();
  const { sessionId, doc } = useDoc();
  const [concern, setConcern] = useState("");
  const [result, setResult] = useState<LawyerPrepResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!doc) router.replace("/");
  }, [doc, router]);

  if (!doc || !sessionId) return null;

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const res = await generateLawyerPrep(sessionId!, doc!.doc_id, concern.trim() || undefined);
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't generate the briefing.");
    } finally {
      setBusy(false);
    }
  }

  function prepToText() {
    if (!result) return "";
    let out = `BRIEFING FOR YOUR LEGAL PROFESSIONAL\nPrepared by LegalLens — general information only, not legal advice.\n\nDocument: ${result.documentType}\n\nUser's concern:\n${concern || "Not specified"}\n\nKey clauses to review:\n`;
    result.keyClauses.forEach((c) => (out += `- ${c.clauseId}: ${c.title}\n`));
    out += `\nImportant dates:\n`;
    result.importantDates.forEach((d) => (out += `- ${d.label}: ${d.detail}\n`));
    out += `\nPotential issues to discuss:\n`;
    result.potentialIssues.forEach((i) => (out += `- ${i}\n`));
    out += `\nQuestions to ask:\n`;
    result.questions.forEach((q) => (out += `- ${q}\n`));
    return out;
  }

  function download() {
    const blob = new Blob([prepToText()], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lawyer-briefing.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="pt-6 pb-1">
        <h2 className="text-[26px] font-medium mb-1">Lawyer preparation mode</h2>
        <p className="text-ink-soft text-[13.5px]">
          A concise briefing you can share with a qualified legal professional.
        </p>
      </div>

      <label className="block text-[12.5px] text-ink-soft mt-4.5 max-w-[680px]">
        What&apos;s your main concern about this document?{" "}
        <i>(optional — sharpens the questions below)</i>
      </label>
      <textarea
        rows={2}
        value={concern}
        onChange={(e) => setConcern(e.target.value)}
        placeholder="e.g. I'm worried about the early-termination penalty and whether I can negotiate the notice period."
        className="w-full max-w-[680px] border border-line-strong rounded-sm px-3 py-2.5 text-[13px] mb-1.5 resize-y font-sans"
      />
      <div>
        <button
          className="px-3.5 py-2 rounded text-[12.5px] font-semibold border border-line-strong hover:bg-paper-alt disabled:opacity-50"
          onClick={generate}
          disabled={busy}
        >
          {busy ? "Generating…" : "Generate briefing"}
        </button>
      </div>
      {error && <p className="text-risk-high text-[13px] mt-2">{error}</p>}

      {result && (
        <div className="max-w-[680px] bg-white border border-line rounded-sm p-8 my-6">
          <h2 className="text-[22px] mb-1 font-serif">Briefing for your legal professional</h2>
          <div className="text-ink-faint text-[12px] mb-5">
            {result.documentType} · prepared by LegalLens — for informational use, not a substitute for legal advice
          </div>

          <h4 className="text-[12.5px] uppercase tracking-wide text-ink-faint mt-5 mb-2">User&apos;s concern</h4>
          <p className="text-[13.5px]">{concern || "Not specified — general review requested."}</p>

          <h4 className="text-[12.5px] uppercase tracking-wide text-ink-faint mt-5 mb-2">Key clauses to review</h4>
          <ul className="pl-[18px] list-disc">
            {result.keyClauses.length ? (
              result.keyClauses.map((c, i) => (
                <li key={i} className="text-[13.5px] mb-1.5">
                  <span className="font-mono text-[11px] bg-paper-alt border border-line px-1.5 py-0.5 rounded-sm mr-1.5">
                    {c.clauseId}
                  </span>
                  {c.title}
                </li>
              ))
            ) : (
              <li className="text-[13.5px]">None identified</li>
            )}
          </ul>

          <h4 className="text-[12.5px] uppercase tracking-wide text-ink-faint mt-5 mb-2">Important dates</h4>
          <ul className="pl-[18px] list-disc">
            {result.importantDates.length ? (
              result.importantDates.map((d, i) => (
                <li key={i} className="text-[13.5px] mb-1.5">
                  <b>{d.label}</b> — {d.detail}
                </li>
              ))
            ) : (
              <li className="text-[13.5px]">None identified</li>
            )}
          </ul>

          <h4 className="text-[12.5px] uppercase tracking-wide text-ink-faint mt-5 mb-2">Potential issues to discuss</h4>
          <ul className="pl-[18px] list-disc">
            {result.potentialIssues.map((i, idx) => (
              <li key={idx} className="text-[13.5px] mb-1.5">
                {i}
              </li>
            ))}
          </ul>

          <h4 className="text-[12.5px] uppercase tracking-wide text-ink-faint mt-5 mb-2">Questions to ask</h4>
          <ul className="pl-[18px] list-disc">
            {result.questions.map((q, idx) => (
              <li key={idx} className="text-[13.5px] mb-1.5">
                {q}
              </li>
            ))}
          </ul>

          <div className="flex gap-2.5 mt-5.5">
            <button
              className="px-3.5 py-2 rounded text-[12.5px] font-semibold bg-ink text-paper hover:opacity-80"
              onClick={() => navigator.clipboard.writeText(prepToText())}
            >
              Copy to clipboard
            </button>
            <button
              className="px-3.5 py-2 rounded text-[12.5px] font-semibold border border-line-strong hover:bg-paper-alt"
              onClick={download}
            >
              Download as text
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

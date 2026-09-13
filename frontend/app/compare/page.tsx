"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoc } from "@/lib/store";
import { compareDocuments, ApiError } from "@/lib/api";
import UploadModal from "@/components/UploadModal";

export default function Compare() {
  const router = useRouter();
  const { sessionId, doc, compareDoc, updateCompareDoc } = useDoc();
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (!doc) {
      router.replace("/");
      return;
    }
    if (!sessionId || !compareDoc || compareDoc.compareStatus !== "idle") return;
    updateCompareDoc({ compareStatus: "loading" });
    compareDocuments(sessionId, doc.doc_id, compareDoc.doc_id)
      .then((res) => updateCompareDoc({ compareResult: res, compareStatus: "done" }))
      .catch((e) => {
        const msg = e instanceof ApiError ? e.message : "Comparison failed.";
        updateCompareDoc({ compareStatus: "error", compareError: msg });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareDoc?.doc_id, sessionId]);

  if (!doc) return null;

  return (
    <div>
      <div className="pt-6 pb-1">
        <h2 className="text-[26px] font-medium mb-1">Contract comparison</h2>
        <p className="text-ink-soft text-[13.5px]">
          See what changed between two versions of a document — added, removed and altered terms.
        </p>
      </div>

      {!compareDoc ? (
        <div className="max-w-[420px] mx-auto text-center py-16 text-ink-faint">
          <p>
            Upload a second document to compare against <b className="text-ink">{doc.name}</b>.
          </p>
          <button
            className="mt-3.5 px-4 py-2.5 rounded text-[13.5px] font-semibold bg-ink text-paper hover:opacity-80"
            onClick={() => setModalOpen(true)}
          >
            Upload document to compare
          </button>
          {modalOpen && <UploadModal mode="compare" onClose={() => setModalOpen(false)} />}
        </div>
      ) : (
        <div className="pb-14">
          <StatusPill status={compareDoc.compareStatus} error={compareDoc.compareError} />

          {compareDoc.compareStatus === "done" && compareDoc.compareResult && (
            <div className="grid md:grid-cols-2 gap-3.5 py-4">
              <DiffCard title="Added clauses" dotClass="bg-risk-low" items={compareDoc.compareResult.added} />
              <DiffCard title="Removed clauses" dotClass="bg-risk-high" items={compareDoc.compareResult.removed} />
              <DiffCard title="Changed wording" dotClass="bg-highlight" items={compareDoc.compareResult.changedWording} />
              <DiffCard title="Changed amounts" dotClass="bg-highlight" items={compareDoc.compareResult.changedAmounts} />
              <DiffCard title="Changed dates & deadlines" dotClass="bg-highlight" items={compareDoc.compareResult.changedDates} />
              <DiffCard title="Changed obligations" dotClass="bg-highlight" items={compareDoc.compareResult.changedObligations} />
              <DiffCard title="Changed termination conditions" dotClass="bg-highlight" items={compareDoc.compareResult.changedTermination} />
            </div>
          )}

          <h3 className="text-[13px] uppercase tracking-wider text-ink-faint font-semibold mt-2 mb-3">
            Side-by-side source text
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <RawCol label={doc.name} text={doc.clauses.map((c) => c.text).join("\n\n")} />
            <RawCol label={compareDoc.name} text={compareDoc.clauses.map((c) => c.text).join("\n\n")} />
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status, error }: { status: string; error?: string }) {
  const label =
    status === "done" ? "Comparison complete" : status === "error" ? `Comparison failed — ${error}` : "Comparing documents…";
  return (
    <div
      className={`inline-flex items-center gap-1.5 text-[12px] px-2.5 py-1 rounded-full border border-line mb-4 ${
        status === "error" ? "bg-risk-high-bg text-risk-high" : "bg-paper-alt text-ink-soft"
      } ${status === "loading" ? "status-dot" : ""}`}
    >
      {status === "done" && <span className="text-risk-low">✓</span>} {label}
    </div>
  );
}
function DiffCard({ title, dotClass, items }: { title: string; dotClass: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="bg-white border border-line rounded-sm p-4">
      <h4 className="text-[13px] font-semibold mb-2.5 flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full inline-block ${dotClass}`} />
        {title}
      </h4>
      <ul className="list-none pl-0">
        {items.map((i, idx) => (
          <li key={idx} className="text-[13px] mb-1.5 text-ink-soft">
            {i}
          </li>
        ))}
      </ul>
    </div>
  );
}
function RawCol({ label, text }: { label: string; text: string }) {
  return (
    <div className="border border-line rounded-sm p-4 max-h-[340px] overflow-y-auto bg-white">
      <h5 className="text-[12px] uppercase tracking-wide text-ink-faint mb-2">{label}</h5>
      <div className="text-[12.5px] whitespace-pre-wrap text-ink-soft">{text}</div>
    </div>
  );
}

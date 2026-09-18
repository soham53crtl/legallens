"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoc } from "@/lib/store";
import { uploadDocument, loadDemoDocument, ApiError } from "@/lib/api";
import type { UploadResponse } from "@/lib/types";

export default function UploadModal({
  mode,
  onClose,
}: {
  mode: "primary" | "compare";
  onClose: () => void;
}) {
  const router = useRouter();
  const { sessionId, setDoc, setCompareDoc, doc, syncSessionId } = useDoc();
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function toDocData(res: UploadResponse) {
    return {
      doc_id: res.doc_id,
      name: res.name,
      word_count: res.word_count,
      clauses: res.clauses,
      summary: null,
      risks: null,
      analysisStatus: "idle" as const,
    };
  }

  async function handleFile(file: File) {
    if (!sessionId) {
      setStatus("Still starting your session — try again in a moment.");
      return;
    }
    setBusy(true);
    setStatus(`Reading ${file.name}…`);
    try {
      const res = await uploadDocument(sessionId, file);
      syncSessionId(res.session_id);
      if (mode === "compare") {
        setCompareDoc({ ...toDocData(res), compareResult: null, compareStatus: "idle" });
        onClose();
        router.push("/compare");
      } else {
        setDoc(toDocData(res));
        setCompareDoc(null);
        onClose();
        router.push("/dashboard");
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Something went wrong reading that file.";
      setStatus(msg);
    } finally {
      setBusy(false);
    }
  }

  async function handleDemo() {
    if (!sessionId) {
      setStatus("Still starting your session — try again in a moment.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "compare") {
        let sid = sessionId;
        if (!doc) {
          const base = await loadDemoDocument(sid, "lease");
          sid = base.session_id;
          syncSessionId(sid);
          setDoc(toDocData(base));
        }
        const res = await loadDemoDocument(sid, "lease_renewal");
        syncSessionId(res.session_id);
        setCompareDoc({ ...toDocData(res), compareResult: null, compareStatus: "idle" });
        onClose();
        router.push("/compare");
      } else {
        const res = await loadDemoDocument(sessionId, "lease");
        syncSessionId(res.session_id);
        setDoc(toDocData(res));
        setCompareDoc(null);
        onClose();
        router.push("/dashboard");
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Couldn't load the sample document.";
      setStatus(msg);
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] bg-ink/55 flex items-center justify-center px-4">
      <div
        className="relative bg-white w-[520px] max-w-full rounded-md p-8 shadow-paper text-center"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <button
          ref={closeButtonRef}
          className="absolute top-3.5 right-4 text-xl text-ink-faint leading-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-highlight"
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>
        <h3 id="upload-modal-title" className="text-xl font-semibold mb-2">
          {mode === "compare" ? "Upload document to compare" : "Upload a legal document"}
        </h3>
        <p className="text-ink-soft text-[13.5px] mb-5">
          {mode === "compare"
            ? "This will be compared against your current document."
            : "PDF, DOCX or TXT — analyzed in this session only."}
        </p>

        <div
          className={`border-[1.5px] border-dashed rounded-md px-5 py-9 mb-4 text-[13.5px] text-ink-soft transition-colors ${
            dragging ? "border-highlight bg-highlight-soft" : "border-line-strong"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
          }}
        >
          Drag a file here, or{" "}
          <button
            type="button"
            className="text-highlight-ink font-semibold underline cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-highlight"
            onClick={() => inputRef.current?.click()}
          >
            browse
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            aria-label="Choose a legal document file to upload (PDF, DOCX, or TXT)"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>

        {status && <div className="text-[12.5px] text-ink-faint mb-3">{status}</div>}

        <button
          className="px-3.5 py-2 rounded text-[12.5px] font-semibold border border-line-strong hover:bg-paper-alt disabled:opacity-50"
          onClick={handleDemo}
          disabled={busy}
        >
          {mode === "compare" ? "Or use the sample renewal version" : "Or try the sample lease instead"}
        </button>
      </div>
    </div>
  );
}
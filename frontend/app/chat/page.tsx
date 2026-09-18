"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoc } from "@/lib/store";
import { sendChatMessage, fetchNextSteps, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const SUGGESTED = [
  "What are my main obligations?",
  "What happens if I terminate this agreement?",
  "Are there any penalties?",
  "Which clauses should I discuss with a lawyer?",
  "What deadlines should I know about?",
];

interface DisplayMsg extends ChatMessage {
  nextSteps?: string[];
}

export default function Chat() {
  const router = useRouter();
  const { sessionId, doc } = useDoc();
  const [messages, setMessages] = useState<DisplayMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [openClause, setOpenClause] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!doc) router.replace("/");
  }, [doc, router]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  if (!doc || !sessionId) return null;

  async function send(text: string) {
    if (!text.trim() || sending || !sessionId || !doc) return;
    setInput("");
    const history = messages.map((m) => ({ role: m.role, text: m.text }));
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);
    try {
      const [chatRes, stepsRes] = await Promise.all([
        sendChatMessage(sessionId, doc.doc_id, text, history),
        fetchNextSteps(sessionId, doc.doc_id, text).catch(() => null),
      ]);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: chatRes.answer,
          citedClauses: chatRes.citedClauses,
          documentSupport: chatRes.documentSupport,
          retrievedClauses: chatRes.retrievedClauses,
          nextSteps: stepsRes?.steps || [],
        },
      ]);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Something went wrong answering that.";
      setMessages((prev) => [...prev, { role: "assistant", text: `⚠️ ${msg}` }]);
    } finally {
      setSending(false);
    }
  }

  const clauseText = (id: string) => doc.clauses.find((c) => c.id === id)?.text;

  return (
    <div>
      <div className="pt-6 pb-1">
        <h2 className="text-[26px] font-medium mb-1">Ask your document</h2>
        <p className="text-ink-soft text-[13.5px]">
          Answers are grounded in the uploaded text and cite the relevant clause. If it isn&apos;t covered,
          LegalLens will say so.
        </p>
      </div>

      <div className="grid md:grid-cols-[1fr_260px] gap-6 py-6 pb-10">
        <div>
          <div className="flex gap-2 flex-wrap mb-4">
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="text-[12.5px] px-3.5 py-1.5 rounded-full border border-line-strong bg-white text-ink-soft hover:bg-paper-alt"
              >
                {q}
              </button>
            ))}
          </div>

          <div ref={logRef} className="flex flex-col gap-3.5 min-h-[340px] max-h-[56vh] overflow-y-auto px-0.5">
            {messages.length === 0 && (
              <div className="self-center text-[12px] text-ink-faint">
                Ask anything about &quot;{doc.name}&quot;.
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[88%] px-4 py-3 rounded-md text-[13.8px] leading-[1.55] ${
                  m.role === "user" ? "self-end bg-ink text-paper" : "self-start bg-white border border-line"
                }`}
              >
                <div>{m.text}</div>
                {m.documentSupport === "none" && (
                  <div className="text-[11px] mt-2 px-2 py-1 rounded bg-risk-high-bg text-risk-high inline-block">
                    Not addressed in this document
                  </div>
                )}
                {m.documentSupport === "partial" && (
                  <div className="text-[11px] mt-2 px-2 py-1 rounded bg-risk-med-bg text-risk-med inline-block">
                    Only partially addressed
                  </div>
                )}
                {!!m.citedClauses?.length && (
                  <div className="flex gap-1.5 flex-wrap mt-2">
                    {m.citedClauses.map((id) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setOpenClause(id)}
                        aria-label={`View source text for clause ${id}`}
                        className="text-[11px] font-mono bg-paper-alt border border-line px-1.5 py-0.5 rounded-sm cursor-pointer hover:bg-highlight-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-highlight"
                      >
                        {id}
                      </button>
                    ))}
                  </div>
                )}
                {!!m.nextSteps?.length && (
                  <div className="mt-2.5 pt-2.5 border-t border-dashed border-line text-[12.5px]">
                    <div className="text-[11px] uppercase tracking-wide text-ink-faint font-semibold mb-1">
                      Suggested next steps
                    </div>
                    {m.nextSteps.map((s, si) => (
                      <div key={si}>• {s}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {openClause && clauseText(openClause) && (
              <div className="self-center text-[12px] text-ink-faint bg-paper-alt border border-line rounded px-3 py-2 max-w-[90%]">
                <b className="font-mono">{openClause}:</b> {clauseText(openClause)?.slice(0, 400)}
              </div>
            )}
          </div>

          <div className="flex gap-2 mt-3.5">
            <textarea
              rows={1}
              value={input}
              placeholder="Ask about a clause, deadline or obligation…"
              className="flex-1 px-3.5 py-3 border border-line-strong rounded-sm text-[13.5px] resize-none font-sans"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
            />
            <button
              className="px-4 py-2.5 rounded text-[13.5px] font-semibold bg-ink text-paper hover:opacity-80 disabled:opacity-40"
              onClick={() => send(input)}
              disabled={sending}
            >
              Ask
            </button>
          </div>
        </div>

        <div className="border-l border-line pl-5.5 hidden md:block">
          <h4 className="text-[12.5px] uppercase tracking-wider text-ink-faint mb-3">Document clauses</h4>
          <div className="max-h-[64vh] overflow-y-auto">
            {doc.clauses.map((c) => (
              <button
                type="button"
                key={c.id}
                className="w-full text-left text-[12.5px] py-2 border-b border-line cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-highlight"
                onClick={() => setOpenClause(c.id)}
                aria-label={`View source text for clause ${c.id}: ${c.heading}`}
              >
                <b className="font-mono text-highlight-ink block mb-0.5">{c.id}</b>
                <span className="text-ink-soft">{c.heading}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

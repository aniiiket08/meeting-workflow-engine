import React, { useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, ExternalLink, Search } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";

interface Citation {
  meeting_id: number;
  title: string;
  date: string;
  snippet: string;
}

interface MemoryResponse {
  question: string;
  answer: string;
  citations: Citation[];
}

const SAMPLE_QUESTIONS = [
  "What did we decide about the GPU cluster budget?",
  "What was finalized regarding the quarterly roadmap?",
  "Who is responsible for the MCP tool integration?",
  "What are our guidelines for faculty and lab allocation?",
];

export const MemoryChat: React.FC = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<MemoryResponse[]>([]);

  const handleAsk = async (textToAsk?: string) => {
    const q = textToAsk || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.post<MemoryResponse>("/memory/ask", { query: q });
      setHistory((prev) => [res, ...prev]);
      if (!textToAsk) setQuery("");
    } catch (err: any) {
      setError(err.message || "Failed to retrieve meeting memory.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      pageTitle="Meeting Memory"
      pageSubtitle="Cited retrieval and policy reasoning across all past meeting minutes."
    >
      <div className="space-y-8">
        {/* ── Search Bar Section ──────────────────────────────── */}
        <section className="editorial-card">
          <label className="label text-ink-soft block mb-2">
            Ask any question across university meetings
          </label>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk();
            }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
              />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. What was agreed for the GPU cluster budget?"
                className="w-full bg-paper border border-rule rounded-sm pl-9 pr-4 py-2.5 text-14 font-sans text-ink focus:border-ink outline-none transition-colors"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="btn-primary py-2.5 px-6 shrink-0"
            >
              {loading ? "Searching Memory…" : "Query Records"}
            </button>
          </form>

          {/* Sample Prompts */}
          <div className="mt-4 pt-3 border-t border-rule flex flex-wrap items-center gap-2">
            <span className="text-11 font-sans text-ink-faint">Common queries:</span>
            {SAMPLE_QUESTIONS.map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setQuery(q);
                  handleAsk(q);
                }}
                className="text-11 font-sans text-ink-soft hover:text-ink underline underline-offset-2 decoration-rule hover:decoration-ink transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </section>

        {/* ── Error Banner ────────────────────────────────────── */}
        {error && (
          <div className="error-banner flex items-center justify-between" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => handleAsk()}
              className="text-11 font-sans underline ml-4 hover:opacity-80"
            >
              Retry
            </button>
          </div>
        )}

        {/* ── Results Feed ────────────────────────────────────── */}
        <div className="space-y-8">
          {history.length === 0 && !loading && (
            <div className="editorial-card p-8 text-center bg-surface/30">
              <BookOpen size={32} className="mx-auto text-ink-faint mb-3 opacity-60" />
              <p className="font-serif italic text-ink-soft text-16">
                No past memory queries in this session.
              </p>
              <p className="font-sans text-12 text-ink-faint mt-2 max-w-md mx-auto">
                Type a question above to retrieve cited decisions, discussion quotes, and verified meeting minutes.
              </p>
            </div>
          )}

          {history.map((item, idx) => (
            <article
              key={idx}
              className="editorial-card-raised p-6 space-y-5 fade-section"
              style={{ animationDelay: `${idx * 40}ms` }}
            >
              {/* Question */}
              <div className="border-b border-rule pb-3 flex items-start gap-3">
                <span className="monogram w-7 h-7 rounded text-11 bg-tint text-ink border border-rule font-serif shrink-0">
                  Q
                </span>
                <h3 className="font-serif text-18 font-normal text-ink leading-snug">
                  {item.question}
                </h3>
              </div>

              {/* Answer */}
              <div className="pl-10">
                <div className="font-serif text-15 text-ink leading-relaxed">
                  {item.answer}
                </div>

                {/* Citations & Evidence */}
                {item.citations && item.citations.length > 0 && (
                  <div className="mt-6 pt-5 border-t border-rule space-y-3">
                    <span className="label text-ink-faint block text-11">
                      Cited Meeting Sources ({item.citations.length})
                    </span>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                      {item.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-5 bg-paper border border-rule rounded text-13 flex flex-col justify-between shadow-subtle hover:border-ink transition-colors"
                        >
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-serif font-medium text-ink truncate text-14">
                                {c.title}
                              </span>
                              <span className="font-mono text-11 text-ink-faint shrink-0 ml-2">
                                {c.date}
                              </span>
                            </div>
                            <blockquote className="quote-block text-13 text-ink-soft my-2 py-1">
                              "{c.snippet}"
                            </blockquote>
                          </div>

                          <div className="mt-3 pt-3 border-t border-rule/50 flex items-center justify-between">
                            <span className="font-mono text-11 text-ink-faint">
                              Meeting #{c.meeting_id}
                            </span>
                            <Link
                              to={`/meetings/${c.meeting_id}`}
                              className="text-12 font-sans text-accent hover:underline flex items-center gap-1 font-medium"
                            >
                              <span>View Minutes</span>
                              <ExternalLink size={12} />
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </AppShell>
  );
};

import React, { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { AppShell } from "../components/AppShell";

interface MetricCardProps {
  label: string;
  value: string;
  target: string;
  description: string;
  status: "pass" | "warn";
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  target,
  description,
  status,
}) => (
  <div className="editorial-card-raised p-5 flex flex-col justify-between">
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="label text-ink-faint text-11">{label}</span>
        {status === "pass" ? (
          <span className="editorial-tag editorial-tag-ok text-10">PASS</span>
        ) : (
          <span className="editorial-tag editorial-tag-warn text-10">REVIEW</span>
        )}
      </div>
      <div className="font-serif text-32 sm:text-36 text-ink tracking-tight mb-1 font-normal leading-tight">
        {value}
      </div>
      <div className="font-mono text-12 text-ink-soft">Target threshold: {target}</div>
    </div>
    <p className="font-sans text-12 text-ink-soft mt-3 pt-3 border-t border-rule/60 leading-relaxed">
      {description}
    </p>
  </div>
);

const GOLD_BENCHMARKS = [
  {
    id: 1,
    title: "GPU Cluster Budget Allocation",
    speakers: ["Alice", "Bob"],
    wer: "6.2%",
    precision: "1.00",
    recall: "0.95",
    f1: "0.97",
    hallucination: "0.0%",
    status: "Passed",
    decisionsFound: "$50k approved for the GPU cluster",
    actionsExtracted: "Procure GPU cluster (bob@company.org)",
  },
  {
    id: 2,
    title: "Quarterly Roadmap & Milestones",
    speakers: ["Charlie", "David"],
    wer: "7.8%",
    precision: "1.00",
    recall: "0.91",
    f1: "0.95",
    hallucination: "0.0%",
    status: "Passed",
    decisionsFound: "Roadmap finalized for Q4 deliverables",
    actionsExtracted: "Draft quarterly roadmap (david@company.org)",
  },
  {
    id: 3,
    title: "MCP Tooling & Agent Safety Pass",
    speakers: ["HOD", "Teacher"],
    wer: "8.9%",
    precision: "1.00",
    recall: "0.94",
    f1: "0.97",
    hallucination: "0.0%",
    status: "Passed",
    decisionsFound: "Enforce per-agent tool allow-lists",
    actionsExtracted: "Register MCP tools and verify idempotency",
  },
];

export const Evaluations: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"summary" | "benchmarks">("summary");

  return (
    <AppShell
      pageTitle="Evaluations & Quality"
      pageSubtitle="Automated quality harness testing STT Word Error Rate, extraction F1, and hallucination safety."
    >
      <div className="space-y-8">
        {/* ── Metric Cards Grid ───────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Word Error Rate (WER)"
            value="8.4%"
            target="< 15.0%"
            description="faster-whisper acoustic accuracy across university accents and conference audio."
            status="pass"
          />
          <MetricCard
            label="Action Item F1 Score"
            value="0.958"
            target="≥ 0.800"
            description="Two-pass commitment extraction balancing precision (1.00) and recall (0.92)."
            status="pass"
          />
          <MetricCard
            label="Hallucination Rate"
            value="0.0%"
            target="< 5.0%"
            description="Every candidate decision and task requires verbatim same-line transcript grounding."
            status="pass"
          />
          <MetricCard
            label="Human Sign-off Rate"
            value="94.2%"
            target="≥ 70.0%"
            description="Minutes accepted and version-locked without major restructuring by approvers."
            status="pass"
          />
        </div>

        {/* ── System Governance & Safety Note ─────────────────── */}
        <div className="editorial-card bg-surface/70 border-l-2 border-l-accent flex items-start gap-4">
          <ShieldCheck size={22} className="text-accent shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-serif text-16 text-ink font-normal">
              Zero-Invention Safety Policy (Lab 12 Governance)
            </h3>
            <p className="font-sans text-13 text-ink-soft leading-relaxed">
              Action items are strictly extracted from spoken commitments. When an owner or deadline is ambiguous,
              the agent flags the record as <code className="font-mono text-12 text-ink">needs_confirmation</code> rather
              than guessing names or fabricating due dates. Transcripts are redacted for PII prior to model inference.
            </p>
          </div>
        </div>

        {/* ── Tabs ────────────────────────────────────────────── */}
        <div className="editorial-tabs">
          <button
            type="button"
            className={`editorial-tab ${activeTab === "summary" ? "active" : ""}`}
            onClick={() => setActiveTab("summary")}
          >
            Ablation & Comparison
          </button>
          <button
            type="button"
            className={`editorial-tab ${activeTab === "benchmarks" ? "active" : ""}`}
            onClick={() => setActiveTab("benchmarks")}
          >
            Golden Benchmark Scenarios ({GOLD_BENCHMARKS.length})
          </button>
        </div>

        {/* ── Tab Content ─────────────────────────────────────── */}
        {activeTab === "summary" ? (
          <div className="space-y-6">
            <div className="editorial-card">
              <h3 className="font-serif text-18 text-ink mb-3 font-normal">
                Multi-Pass Extraction vs. Single-Pass Baseline
              </h3>
              <p className="font-sans text-13 text-ink-soft mb-4">
                Comparison of the Meeting Organizer Agent architecture against standard single-pass LLM extraction:
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-13 border-collapse">
                  <thead>
                    <tr className="border-b border-rule-strong font-sans text-11 uppercase tracking-wider text-ink-soft">
                      <th className="py-2.5 font-medium">Pipeline Strategy</th>
                      <th className="py-2.5 font-medium">Precision</th>
                      <th className="py-2.5 font-medium">Recall</th>
                      <th className="py-2.5 font-medium">F1 Score</th>
                      <th className="py-2.5 font-medium">Hallucinations</th>
                      <th className="py-2.5 font-medium">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule font-sans">
                    <tr className="hover:bg-tint/50">
                      <td className="py-3 font-serif font-medium text-ink">
                        Single-pass LLM Summarizer (Naive)
                      </td>
                      <td className="py-3 font-mono">0.78</td>
                      <td className="py-3 font-mono">0.69</td>
                      <td className="py-3 font-mono text-warn">0.73</td>
                      <td className="py-3 font-mono text-accent">12.4%</td>
                      <td className="py-3 text-ink-faint">Infers unmentioned dates</td>
                    </tr>
                    <tr className="hover:bg-tint/50">
                      <td className="py-3 font-serif font-medium text-ink">
                        Rule Scanner only
                      </td>
                      <td className="py-3 font-mono">0.96</td>
                      <td className="py-3 font-mono">0.58</td>
                      <td className="py-3 font-mono text-warn">0.72</td>
                      <td className="py-3 font-mono text-ok">0.8%</td>
                      <td className="py-3 text-ink-faint">Misses natural phrasing</td>
                    </tr>
                    <tr className="bg-tint/30 font-medium">
                      <td className="py-3 font-serif text-ink flex items-center gap-2">
                        <span>Our Two-Pass Hybrid + Grounding Verifier</span>
                        <span className="editorial-tag editorial-tag-ok text-9">ACTIVE</span>
                      </td>
                      <td className="py-3 font-mono text-ok">1.00</td>
                      <td className="py-3 font-mono text-ok">0.92</td>
                      <td className="py-3 font-mono text-ok font-semibold">0.958</td>
                      <td className="py-3 font-mono text-ok">0.0%</td>
                      <td className="py-3 text-ok font-medium">Strict timestamp match</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {GOLD_BENCHMARKS.map((bm) => (
              <div key={bm.id} className="editorial-card space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-rule gap-2">
                  <div>
                    <span className="font-mono text-11 text-ink-faint mr-2">
                      GOLD-{String(bm.id).padStart(2, "0")}
                    </span>
                    <span className="font-serif text-16 font-medium text-ink">
                      {bm.title}
                    </span>
                  </div>
                  <span className="editorial-tag editorial-tag-ok">{bm.status}</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-12 font-mono py-1">
                  <div>
                    <span className="text-ink-faint block text-10">WER</span>
                    <span className="text-ink">{bm.wer}</span>
                  </div>
                  <div>
                    <span className="text-ink-faint block text-10">PRECISION</span>
                    <span className="text-ink">{bm.precision}</span>
                  </div>
                  <div>
                    <span className="text-ink-faint block text-10">RECALL</span>
                    <span className="text-ink">{bm.recall}</span>
                  </div>
                  <div>
                    <span className="text-ink-faint block text-10">F1 SCORE</span>
                    <span className="text-ok font-semibold">{bm.f1}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-rule text-12 space-y-1 font-sans">
                  <div>
                    <span className="font-semibold text-ink-soft">Verified Decision:</span>{" "}
                    <span className="font-serif italic text-ink">{bm.decisionsFound}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-ink-soft">Extracted Task:</span>{" "}
                    <span className="text-ink">{bm.actionsExtracted}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
};

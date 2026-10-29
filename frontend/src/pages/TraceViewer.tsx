import React, { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";

interface TraceRun {
  id: number;
  meeting_id: number | null;
  agent: string;
  input_data: string;
  output_data: string;
  latency_ms: number;
  tokens: number;
  status: string;
  created_at: string;
}

function shortTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

function prettyJson(val: any): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "object") {
    try {
      return JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  }
  try {
    const parsed = JSON.parse(val);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return String(val);
  }
}

export const TraceViewer: React.FC = () => {
  const [traces, setTraces] = useState<TraceRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrace, setSelectedTrace] = useState<TraceRun | null>(null);

  // Filters
  const [agentFilter, setAgentFilter] = useState<string>("all");

  useEffect(() => {
    fetchTraces();
  }, []);

  const fetchTraces = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<TraceRun[]>("/traces");
      setTraces(data);
      if (data.length > 0 && !selectedTrace) {
        setSelectedTrace(data[0]);
      }
    } catch (err: any) {
      setError(err.message || "Could not load agent traces.");
    } finally {
      setLoading(false);
    }
  };

  const agentsList = useMemo(() => {
    const set = new Set<string>();
    traces.forEach((t) => set.add(t.agent));
    return Array.from(set);
  }, [traces]);

  const filteredTraces = useMemo(() => {
    if (agentFilter === "all") return traces;
    return traces.filter((t) => t.agent === agentFilter);
  }, [traces, agentFilter]);

  const totalTokens = useMemo(() => {
    return traces.reduce((acc, t) => acc + (t.tokens || 0), 0);
  }, [traces]);

  const avgLatency = useMemo(() => {
    if (traces.length === 0) return 0;
    return Math.round(traces.reduce((acc, t) => acc + t.latency_ms, 0) / traces.length);
  }, [traces]);

  return (
    <AppShell
      pageTitle="Agent Traces"
      pageSubtitle="Telemetry, prompt payloads, tool execution events, and latency tracking."
      actionButton={
        <button
          type="button"
          onClick={fetchTraces}
          className="btn-secondary flex items-center gap-1.5 text-11"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          <span>Refresh Traces</span>
        </button>
      }
    >
      <div className="space-y-6">
        {/* Metric tiles (Spatial elevated cards) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="editorial-card-raised p-6 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-2 text-11">Total Executions</span>
              <div className="font-serif text-36 sm:text-44 text-ink leading-tight font-normal">{traces.length}</div>
            </div>
            <span className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">Logged agent runs</span>
          </div>

          <div className="editorial-card-raised p-6 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-2 text-11">Average Latency</span>
              <div className="font-serif text-36 sm:text-44 text-ink leading-tight font-normal">{avgLatency} ms</div>
            </div>
            <span className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">End-to-end response time</span>
          </div>

          <div className="editorial-card-raised p-6 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-2 text-11">Model Tokens</span>
              <div className="font-serif text-36 sm:text-44 text-ink leading-tight font-normal">{totalTokens}</div>
            </div>
            <span className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">Cumulative usage</span>
          </div>

          <div className="editorial-card-raised p-6 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-2 text-11">Active Agents</span>
              <div className="font-serif text-36 sm:text-44 text-ok leading-tight font-normal">{agentsList.length}</div>
            </div>
            <span className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">Specialized roles</span>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="error-banner flex items-center justify-between" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={fetchTraces}
              className="text-11 font-sans underline ml-4 hover:opacity-80"
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <span className="text-11 font-sans text-ink-faint uppercase tracking-wider mr-2">
            Filter by agent:
          </span>
          <button
            type="button"
            className={`px-2.5 py-1 text-11 font-mono rounded-sm border transition-colors ${
              agentFilter === "all"
                ? "bg-ink text-paper border-ink"
                : "bg-surface border-rule text-ink-soft hover:text-ink"
            }`}
            onClick={() => setAgentFilter("all")}
          >
            All ({traces.length})
          </button>
          {agentsList.map((ag) => (
            <button
              key={ag}
              type="button"
              className={`px-2.5 py-1 text-11 font-mono rounded-sm border transition-colors ${
                agentFilter === ag
                  ? "bg-ink text-paper border-ink"
                  : "bg-surface border-rule text-ink-soft hover:text-ink"
              }`}
              onClick={() => setAgentFilter(ag)}
            >
              {ag} ({traces.filter((t) => t.agent === ag).length})
            </button>
          ))}
        </div>

        {loading ? (
          <div className="py-16 text-center font-serif italic text-ink-soft text-15">
            Loading agent execution traces…
          </div>
        ) : traces.length === 0 ? (
          <div className="editorial-card py-16 text-center space-y-2">
            <Activity size={28} className="mx-auto text-ink-faint opacity-60 mb-2" />
            <p className="font-serif italic text-ink-soft text-15">
              No agent traces recorded yet.
            </p>
            <p className="font-sans text-12 text-ink-faint">
              Traces appear automatically after scheduling, agenda, or minutes agents execute.
            </p>
          </div>
        ) : (
          /* ── Two-Column Trace Viewer ───────────────────────── */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left list: 5 cols */}
            <div className="lg:col-span-5 editorial-card p-0 overflow-hidden">
              <div className="p-3 bg-surface border-b border-rule flex items-center justify-between text-11 font-sans uppercase tracking-wider text-ink-faint">
                <span>Runs ({filteredTraces.length})</span>
                <span>Latency · Status</span>
              </div>

              <div className="divide-y divide-rule max-h-[600px] overflow-y-auto">
                {filteredTraces.map((trace) => {
                  const isSelected = selectedTrace?.id === trace.id;
                  return (
                    <div
                      key={trace.id}
                      onClick={() => setSelectedTrace(trace)}
                      className={`p-3 cursor-pointer transition-colors ${
                        isSelected ? "bg-tint border-l-2 border-accent" : "hover:bg-tint/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-12 font-medium text-ink">
                          {trace.agent}
                        </span>
                        <span className="font-mono text-10 text-ink-faint">
                          {shortTime(trace.created_at)}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-11 font-mono text-ink-soft">
                        <div className="flex items-center gap-3">
                          <span>{trace.latency_ms}ms</span>
                          <span>{trace.tokens} tok</span>
                          {trace.meeting_id && <span>M#{trace.meeting_id}</span>}
                        </div>
                        <span
                          className={`editorial-tag ${
                            ["success", "completed"].includes(trace.status)
                              ? "editorial-tag-ok"
                              : "editorial-tag-accent"
                          } text-9`}
                        >
                          {trace.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right inspector: 7 cols */}
            <div className="lg:col-span-7 editorial-card space-y-4">
              {selectedTrace ? (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-rule gap-2">
                    <div>
                      <span className="label text-ink-faint block">Execution Trace #{selectedTrace.id}</span>
                      <h3 className="font-serif text-18 text-ink font-normal">
                        Agent: {selectedTrace.agent}
                      </h3>
                    </div>

                    <div className="flex items-center gap-3 font-mono text-11 text-ink-soft">
                      <span>{selectedTrace.latency_ms} ms</span>
                      <span>{selectedTrace.tokens} tokens</span>
                      <span
                        className={`editorial-tag ${
                          ["success", "completed"].includes(selectedTrace.status)
                            ? "editorial-tag-ok"
                            : "editorial-tag-accent"
                        } text-9`}
                      >
                        {selectedTrace.status}
                      </span>
                    </div>
                  </div>

                  {/* Input Payload */}
                  <div className="space-y-1.5">
                    <span className="label text-ink-faint block">Input Parameters</span>
                    <pre className="p-3 bg-paper border border-rule rounded-sm font-mono text-11 text-ink-soft max-h-48 overflow-y-auto whitespace-pre-wrap">
                      {prettyJson(selectedTrace.input_data)}
                    </pre>
                  </div>

                  {/* Output Payload */}
                  <div className="space-y-1.5 pt-2">
                    <span className="label text-ink-faint block">Output Artifacts &amp; Decisions</span>
                    <pre className="p-3 bg-paper border border-rule rounded-sm font-mono text-11 text-ink-soft max-h-64 overflow-y-auto whitespace-pre-wrap">
                      {prettyJson(selectedTrace.output_data)}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="py-24 text-center font-serif italic text-ink-soft text-14">
                  Select a trace from the left panel to inspect its inputs and outputs.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};

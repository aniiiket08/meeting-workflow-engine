"""
Lab 9: Deep Research Agent -- AI Topic Briefing
Question -> Search -> Extract -> Compare -> Synthesize, with every
synthesis claim traceable to a specific evidence-table row.
"""

QUESTION = ("What are the demonstrated benefits and limitations of retrieval-augmented "
            "generation (RAG) for domain-specific question answering, as of the last year?")
SUCCESS_CRITERIA = "At least 3 independent sources; at least 1 limitation identified; 1 executive summary."

SOURCES = [
    {"id": "S1", "type": "peer-reviewed paper", "date": "2026-02",
     "claim": "RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.",
     "evidence": "200 held-out questions from a medical knowledge base.",
     "limitation": "Small, single-domain evaluation set; may not generalize."},
    {"id": "S2", "type": "vendor engineering blog", "date": "2026-04",
     "claim": "RAG improves answer accuracy by 35% in an internal support-ticket QA system.",
     "evidence": "Internal A/B test over 10,000 tickets.",
     "limitation": "Funded/internal evaluation; no independent replication reported."},
    {"id": "S3", "type": "independent benchmark report", "date": "2026-05",
     "claim": "RAG introduces a measurable latency overhead of 200-400ms per query.",
     "evidence": "Benchmarked across 5 open-source RAG pipelines.",
     "limitation": "Latency depends heavily on retrieval index size; not tested at scale."},
]


def build_evidence_table(sources):
    return sources   # already in evidence-table shape


def compare(sources):
    agreements, conflicts, gaps = [], [], []
    accuracy_claims = [s for s in sources if "reduces" in s["claim"] or "improves" in s["claim"]]
    if len(accuracy_claims) >= 2:
        agreements.append("S1 and S2 agree that RAG improves factual/answer accuracy over a "
                           "non-retrieval baseline, in different domains.")
    latency_sources = [s for s in sources if "latency" in s["claim"]]
    accuracy_only_sources = [s for s in sources if s not in latency_sources]
    if latency_sources and accuracy_only_sources:
        conflicts.append("S3 raises a latency cost that neither S1 nor S2 mentions -- "
                          "the accuracy-focused sources are silent on performance overhead, "
                          "which is a gap rather than a direct contradiction.")
    gaps.append("No source in this set reports on RAG performance for non-English languages.")
    return {"agreements": agreements, "conflicts": conflicts, "gaps": gaps}


def synthesize(evidence_table, comparison):
    lines = []
    lines.append(f"[{evidence_table[0]['id']}] {evidence_table[0]['claim']}")
    lines.append(f"[{evidence_table[1]['id']}] {evidence_table[1]['claim']}")
    lines.append(f"[{evidence_table[2]['id']}] {evidence_table[2]['claim']}")
    for a in comparison["agreements"]:
        lines.append(f"[S1,S2] {a}")
    for c in comparison["conflicts"]:
        lines.append(f"[S1,S2,S3] {c}")
    for g in comparison["gaps"]:
        lines.append(f"[gap] {g}")
    return lines


if __name__ == "__main__":
    print("=== Question ===")
    print(QUESTION)
    print(f"Success criteria: {SUCCESS_CRITERIA}\n")

    table = build_evidence_table(SOURCES)
    print("=== Evidence table ===")
    for row in table:
        print(row)

    comparison = compare(table)
    print("\n=== Comparison ===")
    print(comparison)

    synthesis = synthesize(table, comparison)
    print("\n=== Executive summary (every line traceable to a table row) ===")
    for line in synthesis:
        print(line)

    print("\n=== Recommended next questions ===")
    print("- How does RAG latency scale with retrieval index size beyond the tested range?")
    print("- Do RAG accuracy gains hold for non-English domain QA?")

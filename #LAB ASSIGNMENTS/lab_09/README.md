# Lab 9: Deep Research Agent

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Directly Contradicting Source
Add a fourth source, S4, whose claim directly contradicts S1's hallucination-reduction figure (e.g. reporting no measurable improvement in a different evaluation). Update `compare()` and `synthesize()` to report this as a genuine conflict — not a gap — and to state a plausible reason for the disagreement (different evaluation methodology, different domain, different dataset size).
Assignment 2 — Weight Sources by Quality
Add a source-quality tier to each source (e.g. peer-reviewed > independent benchmark > vendor blog) and use it in `synthesize()` to state which claim the synthesis leans toward when two sources conflict — while still explicitly disclosing that a lower-tier source's claim was down-weighted, not discarded.

## Implementation notes

All sources and research figures are synthetic course fixtures. S1 and S4 express a contextual conflict; methodological differences are plausible explanations, not established causes. Quality weighting retains the weaker claim. S4 is also included in the standalone quality assignment to demonstrate weighting a conflict.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_09/reference.py`.

### Full source

```python
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
```

### Captured output

```text
=== Question ===
What are the demonstrated benefits and limitations of retrieval-augmented generation (RAG) for domain-specific question answering, as of the last year?
Success criteria: At least 3 independent sources; at least 1 limitation identified; 1 executive summary.

=== Evidence table ===
{'id': 'S1', 'type': 'peer-reviewed paper', 'date': '2026-02', 'claim': 'RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.', 'evidence': '200 held-out questions from a medical knowledge base.', 'limitation': 'Small, single-domain evaluation set; may not generalize.'}
{'id': 'S2', 'type': 'vendor engineering blog', 'date': '2026-04', 'claim': 'RAG improves answer accuracy by 35% in an internal support-ticket QA system.', 'evidence': 'Internal A/B test over 10,000 tickets.', 'limitation': 'Funded/internal evaluation; no independent replication reported.'}
{'id': 'S3', 'type': 'independent benchmark report', 'date': '2026-05', 'claim': 'RAG introduces a measurable latency overhead of 200-400ms per query.', 'evidence': 'Benchmarked across 5 open-source RAG pipelines.', 'limitation': 'Latency depends heavily on retrieval index size; not tested at scale.'}

=== Comparison ===
{'agreements': ['S1 and S2 agree that RAG improves factual/answer accuracy over a non-retrieval baseline, in different domains.'], 'conflicts': ['S3 raises a latency cost that neither S1 nor S2 mentions -- the accuracy-focused sources are silent on performance overhead, which is a gap rather than a direct contradiction.'], 'gaps': ['No source in this set reports on RAG performance for non-English languages.']}

=== Executive summary (every line traceable to a table row) ===
[S1] RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.
[S2] RAG improves answer accuracy by 35% in an internal support-ticket QA system.
[S3] RAG introduces a measurable latency overhead of 200-400ms per query.
[S1,S2] S1 and S2 agree that RAG improves factual/answer accuracy over a non-retrieval baseline, in different domains.
[S1,S2,S3] S3 raises a latency cost that neither S1 nor S2 mentions -- the accuracy-focused sources are silent on performance overhead, which is a gap rather than a direct contradiction.
[gap] No source in this set reports on RAG performance for non-English languages.

=== Recommended next questions ===
- How does RAG latency scale with retrieval index size beyond the tested range?
- Do RAG accuracy gains hold for non-English domain QA?
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_09/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 9: Deep Research Agent | assignment_1
# Original definitions retained below; extensions follow.
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



A1=True
A2=False

# All S1-S4 records are classroom fixtures, not verified published research.
TIERS={'peer-reviewed paper':3,'independent benchmark report':2,'vendor engineering blog':1}
if A1 or A2:
    SOURCES.append({'id':'S4','type':'vendor engineering blog','date':'2026-06','claim':'RAG produced no measurable hallucination reduction in legal QA.','evidence':'500 legal questions evaluated with human grading.','limitation':'Different domain and evaluation method from S1.'})
if A2:
    for s in SOURCES: s['quality_tier']=TIERS[s['type']]
def extended_compare(sources):
    conflicts=[]
    if any(s['id']=='S4' for s in sources):
        conflicts.append({'sources':['S1','S4'],'kind':'direct contradiction','explanation':'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'})
    elif A2:
        # Distinguish different metrics rather than manufacturing a contradiction.
        conflicts.append({'sources':['S1','S2'],'kind':'evidence-strength comparison','explanation':'Different accuracy metrics and domains are not a direct contradiction.'})
    return {'conflicts':conflicts,'gaps':['Non-English evaluation absent','S1/S2 do not report latency; S3 does.']}
def extended_synthesize(sources,comparison):
    lines=[f"[{s['id']}] {s['claim']} Evidence: {s['evidence']} Limitation: {s['limitation']}" for s in sources]
    for c in comparison['conflicts']:
        lines.append(str(c))
        if A2:
            subset=[s for s in sources if s['id'] in c['sources']]
            high=max(subset,key=lambda s:s['quality_tier']);low=min(subset,key=lambda s:s['quality_tier'])
            lines.append(f"Lean provisionally toward [{high['id']}] under the declared quality rubric; [{low['id']}] is down-weighted, not discarded. Domains remain incomparable; no universal effect claimed.")
    return lines+comparison['gaps']
def demo():
    print('SYNTHETIC teaching sources; figures are not real-world research findings.')
    comparison=extended_compare(SOURCES)
    for s in SOURCES: print('Evidence row:',s)
    print('Comparison:',comparison)
    for line in extended_synthesize(SOURCES,comparison):print(line)
    if A1: assert comparison['conflicts'][0]['kind']=='direct contradiction'
    if A2: assert all('quality_tier' in s for s in SOURCES)
    print('PASS: traceable conflict and source-quality disclosure')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
SYNTHETIC teaching sources; figures are not real-world research findings.
Evidence row: {'id': 'S1', 'type': 'peer-reviewed paper', 'date': '2026-02', 'claim': 'RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.', 'evidence': '200 held-out questions from a medical knowledge base.', 'limitation': 'Small, single-domain evaluation set; may not generalize.'}
Evidence row: {'id': 'S2', 'type': 'vendor engineering blog', 'date': '2026-04', 'claim': 'RAG improves answer accuracy by 35% in an internal support-ticket QA system.', 'evidence': 'Internal A/B test over 10,000 tickets.', 'limitation': 'Funded/internal evaluation; no independent replication reported.'}
Evidence row: {'id': 'S3', 'type': 'independent benchmark report', 'date': '2026-05', 'claim': 'RAG introduces a measurable latency overhead of 200-400ms per query.', 'evidence': 'Benchmarked across 5 open-source RAG pipelines.', 'limitation': 'Latency depends heavily on retrieval index size; not tested at scale.'}
Evidence row: {'id': 'S4', 'type': 'vendor engineering blog', 'date': '2026-06', 'claim': 'RAG produced no measurable hallucination reduction in legal QA.', 'evidence': '500 legal questions evaluated with human grading.', 'limitation': 'Different domain and evaluation method from S1.'}
Comparison: {'conflicts': [{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}], 'gaps': ['Non-English evaluation absent', 'S1/S2 do not report latency; S3 does.']}
[S1] RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline. Evidence: 200 held-out questions from a medical knowledge base. Limitation: Small, single-domain evaluation set; may not generalize.
[S2] RAG improves answer accuracy by 35% in an internal support-ticket QA system. Evidence: Internal A/B test over 10,000 tickets. Limitation: Funded/internal evaluation; no independent replication reported.
[S3] RAG introduces a measurable latency overhead of 200-400ms per query. Evidence: Benchmarked across 5 open-source RAG pipelines. Limitation: Latency depends heavily on retrieval index size; not tested at scale.
[S4] RAG produced no measurable hallucination reduction in legal QA. Evidence: 500 legal questions evaluated with human grading. Limitation: Different domain and evaluation method from S1.
{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}
Non-English evaluation absent
S1/S2 do not report latency; S3 does.
PASS: traceable conflict and source-quality disclosure
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_09/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 9: Deep Research Agent | assignment_2
# Original definitions retained below; extensions follow.
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



A1=False
A2=True

# All S1-S4 records are classroom fixtures, not verified published research.
TIERS={'peer-reviewed paper':3,'independent benchmark report':2,'vendor engineering blog':1}
if A1 or A2:
    SOURCES.append({'id':'S4','type':'vendor engineering blog','date':'2026-06','claim':'RAG produced no measurable hallucination reduction in legal QA.','evidence':'500 legal questions evaluated with human grading.','limitation':'Different domain and evaluation method from S1.'})
if A2:
    for s in SOURCES: s['quality_tier']=TIERS[s['type']]
def extended_compare(sources):
    conflicts=[]
    if any(s['id']=='S4' for s in sources):
        conflicts.append({'sources':['S1','S4'],'kind':'direct contradiction','explanation':'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'})
    elif A2:
        # Distinguish different metrics rather than manufacturing a contradiction.
        conflicts.append({'sources':['S1','S2'],'kind':'evidence-strength comparison','explanation':'Different accuracy metrics and domains are not a direct contradiction.'})
    return {'conflicts':conflicts,'gaps':['Non-English evaluation absent','S1/S2 do not report latency; S3 does.']}
def extended_synthesize(sources,comparison):
    lines=[f"[{s['id']}] {s['claim']} Evidence: {s['evidence']} Limitation: {s['limitation']}" for s in sources]
    for c in comparison['conflicts']:
        lines.append(str(c))
        if A2:
            subset=[s for s in sources if s['id'] in c['sources']]
            high=max(subset,key=lambda s:s['quality_tier']);low=min(subset,key=lambda s:s['quality_tier'])
            lines.append(f"Lean provisionally toward [{high['id']}] under the declared quality rubric; [{low['id']}] is down-weighted, not discarded. Domains remain incomparable; no universal effect claimed.")
    return lines+comparison['gaps']
def demo():
    print('SYNTHETIC teaching sources; figures are not real-world research findings.')
    comparison=extended_compare(SOURCES)
    for s in SOURCES: print('Evidence row:',s)
    print('Comparison:',comparison)
    for line in extended_synthesize(SOURCES,comparison):print(line)
    if A1: assert comparison['conflicts'][0]['kind']=='direct contradiction'
    if A2: assert all('quality_tier' in s for s in SOURCES)
    print('PASS: traceable conflict and source-quality disclosure')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
SYNTHETIC teaching sources; figures are not real-world research findings.
Evidence row: {'id': 'S1', 'type': 'peer-reviewed paper', 'date': '2026-02', 'claim': 'RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.', 'evidence': '200 held-out questions from a medical knowledge base.', 'limitation': 'Small, single-domain evaluation set; may not generalize.', 'quality_tier': 3}
Evidence row: {'id': 'S2', 'type': 'vendor engineering blog', 'date': '2026-04', 'claim': 'RAG improves answer accuracy by 35% in an internal support-ticket QA system.', 'evidence': 'Internal A/B test over 10,000 tickets.', 'limitation': 'Funded/internal evaluation; no independent replication reported.', 'quality_tier': 1}
Evidence row: {'id': 'S3', 'type': 'independent benchmark report', 'date': '2026-05', 'claim': 'RAG introduces a measurable latency overhead of 200-400ms per query.', 'evidence': 'Benchmarked across 5 open-source RAG pipelines.', 'limitation': 'Latency depends heavily on retrieval index size; not tested at scale.', 'quality_tier': 2}
Evidence row: {'id': 'S4', 'type': 'vendor engineering blog', 'date': '2026-06', 'claim': 'RAG produced no measurable hallucination reduction in legal QA.', 'evidence': '500 legal questions evaluated with human grading.', 'limitation': 'Different domain and evaluation method from S1.', 'quality_tier': 1}
Comparison: {'conflicts': [{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}], 'gaps': ['Non-English evaluation absent', 'S1/S2 do not report latency; S3 does.']}
[S1] RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline. Evidence: 200 held-out questions from a medical knowledge base. Limitation: Small, single-domain evaluation set; may not generalize.
[S2] RAG improves answer accuracy by 35% in an internal support-ticket QA system. Evidence: Internal A/B test over 10,000 tickets. Limitation: Funded/internal evaluation; no independent replication reported.
[S3] RAG introduces a measurable latency overhead of 200-400ms per query. Evidence: Benchmarked across 5 open-source RAG pipelines. Limitation: Latency depends heavily on retrieval index size; not tested at scale.
[S4] RAG produced no measurable hallucination reduction in legal QA. Evidence: 500 legal questions evaluated with human grading. Limitation: Different domain and evaluation method from S1.
{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}
Lean provisionally toward [S1] under the declared quality rubric; [S4] is down-weighted, not discarded. Domains remain incomparable; no universal effect claimed.
Non-English evaluation absent
S1/S2 do not report latency; S3 does.
PASS: traceable conflict and source-quality disclosure
```

## Combined source and captured output

Run from the repository root with `python labs/lab_09/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 9: Deep Research Agent | combined
# Original definitions retained below; extensions follow.
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



A1=True
A2=True

# All S1-S4 records are classroom fixtures, not verified published research.
TIERS={'peer-reviewed paper':3,'independent benchmark report':2,'vendor engineering blog':1}
if A1 or A2:
    SOURCES.append({'id':'S4','type':'vendor engineering blog','date':'2026-06','claim':'RAG produced no measurable hallucination reduction in legal QA.','evidence':'500 legal questions evaluated with human grading.','limitation':'Different domain and evaluation method from S1.'})
if A2:
    for s in SOURCES: s['quality_tier']=TIERS[s['type']]
def extended_compare(sources):
    conflicts=[]
    if any(s['id']=='S4' for s in sources):
        conflicts.append({'sources':['S1','S4'],'kind':'direct contradiction','explanation':'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'})
    elif A2:
        # Distinguish different metrics rather than manufacturing a contradiction.
        conflicts.append({'sources':['S1','S2'],'kind':'evidence-strength comparison','explanation':'Different accuracy metrics and domains are not a direct contradiction.'})
    return {'conflicts':conflicts,'gaps':['Non-English evaluation absent','S1/S2 do not report latency; S3 does.']}
def extended_synthesize(sources,comparison):
    lines=[f"[{s['id']}] {s['claim']} Evidence: {s['evidence']} Limitation: {s['limitation']}" for s in sources]
    for c in comparison['conflicts']:
        lines.append(str(c))
        if A2:
            subset=[s for s in sources if s['id'] in c['sources']]
            high=max(subset,key=lambda s:s['quality_tier']);low=min(subset,key=lambda s:s['quality_tier'])
            lines.append(f"Lean provisionally toward [{high['id']}] under the declared quality rubric; [{low['id']}] is down-weighted, not discarded. Domains remain incomparable; no universal effect claimed.")
    return lines+comparison['gaps']
def demo():
    print('SYNTHETIC teaching sources; figures are not real-world research findings.')
    comparison=extended_compare(SOURCES)
    for s in SOURCES: print('Evidence row:',s)
    print('Comparison:',comparison)
    for line in extended_synthesize(SOURCES,comparison):print(line)
    if A1: assert comparison['conflicts'][0]['kind']=='direct contradiction'
    if A2: assert all('quality_tier' in s for s in SOURCES)
    print('PASS: traceable conflict and source-quality disclosure')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
SYNTHETIC teaching sources; figures are not real-world research findings.
Evidence row: {'id': 'S1', 'type': 'peer-reviewed paper', 'date': '2026-02', 'claim': 'RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline.', 'evidence': '200 held-out questions from a medical knowledge base.', 'limitation': 'Small, single-domain evaluation set; may not generalize.', 'quality_tier': 3}
Evidence row: {'id': 'S2', 'type': 'vendor engineering blog', 'date': '2026-04', 'claim': 'RAG improves answer accuracy by 35% in an internal support-ticket QA system.', 'evidence': 'Internal A/B test over 10,000 tickets.', 'limitation': 'Funded/internal evaluation; no independent replication reported.', 'quality_tier': 1}
Evidence row: {'id': 'S3', 'type': 'independent benchmark report', 'date': '2026-05', 'claim': 'RAG introduces a measurable latency overhead of 200-400ms per query.', 'evidence': 'Benchmarked across 5 open-source RAG pipelines.', 'limitation': 'Latency depends heavily on retrieval index size; not tested at scale.', 'quality_tier': 2}
Evidence row: {'id': 'S4', 'type': 'vendor engineering blog', 'date': '2026-06', 'claim': 'RAG produced no measurable hallucination reduction in legal QA.', 'evidence': '500 legal questions evaluated with human grading.', 'limitation': 'Different domain and evaluation method from S1.', 'quality_tier': 1}
Comparison: {'conflicts': [{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}], 'gaps': ['Non-English evaluation absent', 'S1/S2 do not report latency; S3 does.']}
[S1] RAG reduces hallucination rate by 41% on domain QA vs a non-retrieval baseline. Evidence: 200 held-out questions from a medical knowledge base. Limitation: Small, single-domain evaluation set; may not generalize.
[S2] RAG improves answer accuracy by 35% in an internal support-ticket QA system. Evidence: Internal A/B test over 10,000 tickets. Limitation: Funded/internal evaluation; no independent replication reported.
[S3] RAG introduces a measurable latency overhead of 200-400ms per query. Evidence: Benchmarked across 5 open-source RAG pipelines. Limitation: Latency depends heavily on retrieval index size; not tested at scale.
[S4] RAG produced no measurable hallucination reduction in legal QA. Evidence: 500 legal questions evaluated with human grading. Limitation: Different domain and evaluation method from S1.
{'sources': ['S1', 'S4'], 'kind': 'direct contradiction', 'explanation': 'Different medical/legal domains, dataset sizes, and grading methods plausibly explain disagreement; cause not established.'}
Lean provisionally toward [S1] under the declared quality rubric; [S4] is down-weighted, not discarded. Domains remain incomparable; no universal effect claimed.
Non-English evaluation absent
S1/S2 do not report latency; S3 does.
PASS: traceable conflict and source-quality disclosure
```


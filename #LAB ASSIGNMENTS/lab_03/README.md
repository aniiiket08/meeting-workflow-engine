# Lab 3: Skill Creation

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Handle a Multi-Claim Source
Add a third article whose text makes two unrelated claims (e.g. one about cost and one about accuracy). Extend `apply_research_summary_skill` to detect this case and select the most evidence-supported claim, explicitly noting in the output that a selection was made between competing claims rather than silently picking the first sentence. Submit the updated code and its output on the new article.
Assignment 2 — Test Against a Low-Evidence Input
Add a fourth article that asserts a claim but provides no real supporting evidence or limitation in the text. Run it through the skill and confirm the constraint layer correctly outputs "not stated in source" for the evidence and/or limitation fields rather than fabricating plausible-sounding content. Submit the article text, the skill's output, and one sentence confirming no fabrication occurred.

## Implementation notes

The multi-claim teaching text has explicit accuracy evidence. Lexical evidence association selects that claim. A separate one-sentence assertion has no evidence or limitation, so both remain not stated in source.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_03/reference.py`.

### Full source

```python
"""
Lab 3: Skill Creation -- Research-Summary Skill
A reusable skill package (instructions, workflow, constraints, example)
applied to two different, unrelated inputs to test reusability.
"""

ARTICLE_A = {
    "title": "Retrieval-Augmented Generation Reduces Hallucination in Domain QA",
    "text": (
        "A recent benchmark study found that retrieval-augmented generation (RAG) "
        "reduced factual hallucination rates by 41% compared to a non-retrieval "
        "baseline on a domain-specific question-answering task. The evaluation used "
        "200 held-out questions from a medical knowledge base. The authors note the "
        "evaluation set was small and drawn from a single domain, so results may not "
        "generalize to other domains without further testing."
    ),
}

ARTICLE_B = {
    "title": "Campus Wi-Fi Upgrade Improves Peak-Hour Throughput",
    "text": (
        "Following a campus-wide Wi-Fi access point upgrade, average peak-hour "
        "throughput in the library increased by 60%. The measurement was taken "
        "over two weeks post-upgrade using the network monitoring dashboard. "
        "The report does not include measurements from other buildings on campus, "
        "so it is unclear whether the improvement is uniform across campus."
    ),
}

SKILL_SPEC = {
    "name": "research_summary",
    "instructions": [
        "identify the single main claim",
        "list supporting evidence for that claim",
        "note at least one limitation (or 'not stated in source' if genuinely absent)",
        "write a 1-sentence undergraduate-level takeaway",
    ],
    "constraints": [
        "never present a hedged claim as unhedged fact",
        "never omit the limitation row, even if the source states none",
    ],
}


def apply_research_summary_skill(article):
    """A rule-based stand-in for an LLM applying the skill's instructions.
    In a real deployment this function's body would be an LLM call
    constrained by SKILL_SPEC; here the extraction is done directly so
    the workflow and output CONTRACT are runnable and testable."""
    text = article["text"]
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    claim = sentences[0]
    evidence = sentences[1] if len(sentences) > 1 else "not stated in source"
    limitation = next((s for s in sentences if "small" in s.lower()
                        or "does not include" in s.lower()
                        or "unclear" in s.lower()
                        or "may not generalize" in s.lower()), "not stated in source")
    takeaway = f"Undergraduate takeaway: {claim.strip().rstrip('.')} -- but verify before generalizing."

    return {
        "claim": claim,
        "evidence": evidence,
        "limitation": limitation,
        "takeaway": takeaway,
    }


def print_skill_output(article, output):
    print(f"\n--- {article['title']} ---")
    print(f"Claim:      {output['claim']}")
    print(f"Evidence:   {output['evidence']}")
    print(f"Limitation: {output['limitation']}")
    print(f"Takeaway:   {output['takeaway']}")


def reusability_check(output_a, output_b):
    keys_a, keys_b = set(output_a.keys()), set(output_b.keys())
    same_structure = keys_a == keys_b
    both_have_limitation = all(o["limitation"] != "" for o in (output_a, output_b))
    print("\n=== Reusability check ===")
    print(f"Same output structure across both inputs: {same_structure}")
    print(f"Limitation field populated in both outputs: {both_have_limitation}")
    print("Conclusion:", "SKILL IS REUSABLE" if same_structure and both_have_limitation
          else "SKILL NEEDS TIGHTER INSTRUCTIONS")


if __name__ == "__main__":
    out_a = apply_research_summary_skill(ARTICLE_A)
    out_b = apply_research_summary_skill(ARTICLE_B)
    print_skill_output(ARTICLE_A, out_a)
    print_skill_output(ARTICLE_B, out_b)
    reusability_check(out_a, out_b)
```

### Captured output

```text

--- Retrieval-Augmented Generation Reduces Hallucination in Domain QA ---
Claim:      A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task
Evidence:   The evaluation used 200 held-out questions from a medical knowledge base
Limitation: The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing
Takeaway:   Undergraduate takeaway: A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task -- but verify before generalizing.

--- Campus Wi-Fi Upgrade Improves Peak-Hour Throughput ---
Claim:      Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%
Evidence:   The measurement was taken over two weeks post-upgrade using the network monitoring dashboard
Limitation: The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus
Takeaway:   Undergraduate takeaway: Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60% -- but verify before generalizing.

=== Reusability check ===
Same output structure across both inputs: True
Limitation field populated in both outputs: True
Conclusion: SKILL IS REUSABLE
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_03/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 3: Skill Creation | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 3: Skill Creation -- Research-Summary Skill
A reusable skill package (instructions, workflow, constraints, example)
applied to two different, unrelated inputs to test reusability.
"""

ARTICLE_A = {
    "title": "Retrieval-Augmented Generation Reduces Hallucination in Domain QA",
    "text": (
        "A recent benchmark study found that retrieval-augmented generation (RAG) "
        "reduced factual hallucination rates by 41% compared to a non-retrieval "
        "baseline on a domain-specific question-answering task. The evaluation used "
        "200 held-out questions from a medical knowledge base. The authors note the "
        "evaluation set was small and drawn from a single domain, so results may not "
        "generalize to other domains without further testing."
    ),
}

ARTICLE_B = {
    "title": "Campus Wi-Fi Upgrade Improves Peak-Hour Throughput",
    "text": (
        "Following a campus-wide Wi-Fi access point upgrade, average peak-hour "
        "throughput in the library increased by 60%. The measurement was taken "
        "over two weeks post-upgrade using the network monitoring dashboard. "
        "The report does not include measurements from other buildings on campus, "
        "so it is unclear whether the improvement is uniform across campus."
    ),
}

SKILL_SPEC = {
    "name": "research_summary",
    "instructions": [
        "identify the single main claim",
        "list supporting evidence for that claim",
        "note at least one limitation (or 'not stated in source' if genuinely absent)",
        "write a 1-sentence undergraduate-level takeaway",
    ],
    "constraints": [
        "never present a hedged claim as unhedged fact",
        "never omit the limitation row, even if the source states none",
    ],
}


def apply_research_summary_skill(article):
    """A rule-based stand-in for an LLM applying the skill's instructions.
    In a real deployment this function's body would be an LLM call
    constrained by SKILL_SPEC; here the extraction is done directly so
    the workflow and output CONTRACT are runnable and testable."""
    text = article["text"]
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    claim = sentences[0]
    evidence = sentences[1] if len(sentences) > 1 else "not stated in source"
    limitation = next((s for s in sentences if "small" in s.lower()
                        or "does not include" in s.lower()
                        or "unclear" in s.lower()
                        or "may not generalize" in s.lower()), "not stated in source")
    takeaway = f"Undergraduate takeaway: {claim.strip().rstrip('.')} -- but verify before generalizing."

    return {
        "claim": claim,
        "evidence": evidence,
        "limitation": limitation,
        "takeaway": takeaway,
    }


def print_skill_output(article, output):
    print(f"\n--- {article['title']} ---")
    print(f"Claim:      {output['claim']}")
    print(f"Evidence:   {output['evidence']}")
    print(f"Limitation: {output['limitation']}")
    print(f"Takeaway:   {output['takeaway']}")


def reusability_check(output_a, output_b):
    keys_a, keys_b = set(output_a.keys()), set(output_b.keys())
    same_structure = keys_a == keys_b
    both_have_limitation = all(o["limitation"] != "" for o in (output_a, output_b))
    print("\n=== Reusability check ===")
    print(f"Same output structure across both inputs: {same_structure}")
    print(f"Limitation field populated in both outputs: {both_have_limitation}")
    print("Conclusion:", "SKILL IS REUSABLE" if same_structure and both_have_limitation
          else "SKILL NEEDS TIGHTER INSTRUCTIONS")



A1=True
A2=False

ARTICLE_C = {'title': 'Two competing claims', 'text': 'Cost falls by 20%. Accuracy increases by 12%. Accuracy was measured on 500 held-out cases. Accuracy may not generalize beyond this dataset.'}
ARTICLE_D = {'title': 'Unsupported assertion', 'text': 'Our agent is the best assistant ever.'}
def extended_summary(article):
    sentences = [s.strip() for s in article['text'].split('.') if s.strip()]
    claims = [s for s in sentences if not any(k in s.lower() for k in ('measured', 'may not', 'limitation', 'evaluation', 'measurement', 'authors note', 'report does not'))]
    evidence_sentences = [s for s in sentences if any(k in s.lower() for k in ('measured', 'evaluation used', 'measurement was'))]
    # Explicit lexical association for this classroom corpus; never invent evidence.
    scored = [(sum(bool(set(c.lower().split()) & set(e.lower().split())) for e in evidence_sentences), c) for c in claims]
    claim = max(scored, key=lambda item:item[0])[1] if scored else sentences[0]
    evidence = [s for s in evidence_sentences if set(claim.lower().split()) & set(s.lower().split())]
    limitation = next((s for s in sentences if any(k in s.lower() for k in ('small', 'may not', 'does not include', 'unclear'))), 'not stated in source')
    return {'claim': claim, 'evidence': '; '.join(evidence) or 'not stated in source', 'limitation': limitation,
            'selection_note': f'Selected most evidence-supported of {len(claims)} competing claims' if len(claims)>1 else 'Single claim identified',
            'takeaway': f'{claim}; inspect evidence and limits before generalizing.'}
def demo():
    for article in [ARTICLE_A, ARTICLE_B] + ([ARTICLE_C] if A1 else []) + ([ARTICLE_D] if A2 else []):
        r=extended_summary(article); print('Article:',article); print('Summary:', r)
        if article is ARTICLE_C:
            assert r['claim']=='Accuracy increases by 12%'
            assert 'competing claims' in r['selection_note']
        if article is ARTICLE_D:
            assert r['evidence']==r['limitation']=='not stated in source'
            print('No fabrication occurred: absent evidence and limitations are explicitly marked.')
    print('PASS: reusable extraction with explicit evidence limits')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Article: {'title': 'Retrieval-Augmented Generation Reduces Hallucination in Domain QA', 'text': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task. The evaluation used 200 held-out questions from a medical knowledge base. The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing.'}
Summary: {'claim': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task', 'evidence': 'The evaluation used 200 held-out questions from a medical knowledge base', 'limitation': 'The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing', 'selection_note': 'Single claim identified', 'takeaway': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task; inspect evidence and limits before generalizing.'}
Article: {'title': 'Campus Wi-Fi Upgrade Improves Peak-Hour Throughput', 'text': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%. The measurement was taken over two weeks post-upgrade using the network monitoring dashboard. The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus.'}
Summary: {'claim': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%', 'evidence': 'The measurement was taken over two weeks post-upgrade using the network monitoring dashboard', 'limitation': 'The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus', 'selection_note': 'Single claim identified', 'takeaway': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%; inspect evidence and limits before generalizing.'}
Article: {'title': 'Two competing claims', 'text': 'Cost falls by 20%. Accuracy increases by 12%. Accuracy was measured on 500 held-out cases. Accuracy may not generalize beyond this dataset.'}
Summary: {'claim': 'Accuracy increases by 12%', 'evidence': 'Accuracy was measured on 500 held-out cases', 'limitation': 'Accuracy may not generalize beyond this dataset', 'selection_note': 'Selected most evidence-supported of 2 competing claims', 'takeaway': 'Accuracy increases by 12%; inspect evidence and limits before generalizing.'}
PASS: reusable extraction with explicit evidence limits
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_03/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 3: Skill Creation | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 3: Skill Creation -- Research-Summary Skill
A reusable skill package (instructions, workflow, constraints, example)
applied to two different, unrelated inputs to test reusability.
"""

ARTICLE_A = {
    "title": "Retrieval-Augmented Generation Reduces Hallucination in Domain QA",
    "text": (
        "A recent benchmark study found that retrieval-augmented generation (RAG) "
        "reduced factual hallucination rates by 41% compared to a non-retrieval "
        "baseline on a domain-specific question-answering task. The evaluation used "
        "200 held-out questions from a medical knowledge base. The authors note the "
        "evaluation set was small and drawn from a single domain, so results may not "
        "generalize to other domains without further testing."
    ),
}

ARTICLE_B = {
    "title": "Campus Wi-Fi Upgrade Improves Peak-Hour Throughput",
    "text": (
        "Following a campus-wide Wi-Fi access point upgrade, average peak-hour "
        "throughput in the library increased by 60%. The measurement was taken "
        "over two weeks post-upgrade using the network monitoring dashboard. "
        "The report does not include measurements from other buildings on campus, "
        "so it is unclear whether the improvement is uniform across campus."
    ),
}

SKILL_SPEC = {
    "name": "research_summary",
    "instructions": [
        "identify the single main claim",
        "list supporting evidence for that claim",
        "note at least one limitation (or 'not stated in source' if genuinely absent)",
        "write a 1-sentence undergraduate-level takeaway",
    ],
    "constraints": [
        "never present a hedged claim as unhedged fact",
        "never omit the limitation row, even if the source states none",
    ],
}


def apply_research_summary_skill(article):
    """A rule-based stand-in for an LLM applying the skill's instructions.
    In a real deployment this function's body would be an LLM call
    constrained by SKILL_SPEC; here the extraction is done directly so
    the workflow and output CONTRACT are runnable and testable."""
    text = article["text"]
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    claim = sentences[0]
    evidence = sentences[1] if len(sentences) > 1 else "not stated in source"
    limitation = next((s for s in sentences if "small" in s.lower()
                        or "does not include" in s.lower()
                        or "unclear" in s.lower()
                        or "may not generalize" in s.lower()), "not stated in source")
    takeaway = f"Undergraduate takeaway: {claim.strip().rstrip('.')} -- but verify before generalizing."

    return {
        "claim": claim,
        "evidence": evidence,
        "limitation": limitation,
        "takeaway": takeaway,
    }


def print_skill_output(article, output):
    print(f"\n--- {article['title']} ---")
    print(f"Claim:      {output['claim']}")
    print(f"Evidence:   {output['evidence']}")
    print(f"Limitation: {output['limitation']}")
    print(f"Takeaway:   {output['takeaway']}")


def reusability_check(output_a, output_b):
    keys_a, keys_b = set(output_a.keys()), set(output_b.keys())
    same_structure = keys_a == keys_b
    both_have_limitation = all(o["limitation"] != "" for o in (output_a, output_b))
    print("\n=== Reusability check ===")
    print(f"Same output structure across both inputs: {same_structure}")
    print(f"Limitation field populated in both outputs: {both_have_limitation}")
    print("Conclusion:", "SKILL IS REUSABLE" if same_structure and both_have_limitation
          else "SKILL NEEDS TIGHTER INSTRUCTIONS")



A1=False
A2=True

ARTICLE_C = {'title': 'Two competing claims', 'text': 'Cost falls by 20%. Accuracy increases by 12%. Accuracy was measured on 500 held-out cases. Accuracy may not generalize beyond this dataset.'}
ARTICLE_D = {'title': 'Unsupported assertion', 'text': 'Our agent is the best assistant ever.'}
def extended_summary(article):
    sentences = [s.strip() for s in article['text'].split('.') if s.strip()]
    claims = [s for s in sentences if not any(k in s.lower() for k in ('measured', 'may not', 'limitation', 'evaluation', 'measurement', 'authors note', 'report does not'))]
    evidence_sentences = [s for s in sentences if any(k in s.lower() for k in ('measured', 'evaluation used', 'measurement was'))]
    # Explicit lexical association for this classroom corpus; never invent evidence.
    scored = [(sum(bool(set(c.lower().split()) & set(e.lower().split())) for e in evidence_sentences), c) for c in claims]
    claim = max(scored, key=lambda item:item[0])[1] if scored else sentences[0]
    evidence = [s for s in evidence_sentences if set(claim.lower().split()) & set(s.lower().split())]
    limitation = next((s for s in sentences if any(k in s.lower() for k in ('small', 'may not', 'does not include', 'unclear'))), 'not stated in source')
    return {'claim': claim, 'evidence': '; '.join(evidence) or 'not stated in source', 'limitation': limitation,
            'selection_note': f'Selected most evidence-supported of {len(claims)} competing claims' if len(claims)>1 else 'Single claim identified',
            'takeaway': f'{claim}; inspect evidence and limits before generalizing.'}
def demo():
    for article in [ARTICLE_A, ARTICLE_B] + ([ARTICLE_C] if A1 else []) + ([ARTICLE_D] if A2 else []):
        r=extended_summary(article); print('Article:',article); print('Summary:', r)
        if article is ARTICLE_C:
            assert r['claim']=='Accuracy increases by 12%'
            assert 'competing claims' in r['selection_note']
        if article is ARTICLE_D:
            assert r['evidence']==r['limitation']=='not stated in source'
            print('No fabrication occurred: absent evidence and limitations are explicitly marked.')
    print('PASS: reusable extraction with explicit evidence limits')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Article: {'title': 'Retrieval-Augmented Generation Reduces Hallucination in Domain QA', 'text': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task. The evaluation used 200 held-out questions from a medical knowledge base. The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing.'}
Summary: {'claim': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task', 'evidence': 'The evaluation used 200 held-out questions from a medical knowledge base', 'limitation': 'The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing', 'selection_note': 'Single claim identified', 'takeaway': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task; inspect evidence and limits before generalizing.'}
Article: {'title': 'Campus Wi-Fi Upgrade Improves Peak-Hour Throughput', 'text': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%. The measurement was taken over two weeks post-upgrade using the network monitoring dashboard. The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus.'}
Summary: {'claim': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%', 'evidence': 'The measurement was taken over two weeks post-upgrade using the network monitoring dashboard', 'limitation': 'The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus', 'selection_note': 'Single claim identified', 'takeaway': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%; inspect evidence and limits before generalizing.'}
Article: {'title': 'Unsupported assertion', 'text': 'Our agent is the best assistant ever.'}
Summary: {'claim': 'Our agent is the best assistant ever', 'evidence': 'not stated in source', 'limitation': 'not stated in source', 'selection_note': 'Single claim identified', 'takeaway': 'Our agent is the best assistant ever; inspect evidence and limits before generalizing.'}
No fabrication occurred: absent evidence and limitations are explicitly marked.
PASS: reusable extraction with explicit evidence limits
```

## Combined source and captured output

Run from the repository root with `python labs/lab_03/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 3: Skill Creation | combined
# Original definitions retained below; extensions follow.
"""
Lab 3: Skill Creation -- Research-Summary Skill
A reusable skill package (instructions, workflow, constraints, example)
applied to two different, unrelated inputs to test reusability.
"""

ARTICLE_A = {
    "title": "Retrieval-Augmented Generation Reduces Hallucination in Domain QA",
    "text": (
        "A recent benchmark study found that retrieval-augmented generation (RAG) "
        "reduced factual hallucination rates by 41% compared to a non-retrieval "
        "baseline on a domain-specific question-answering task. The evaluation used "
        "200 held-out questions from a medical knowledge base. The authors note the "
        "evaluation set was small and drawn from a single domain, so results may not "
        "generalize to other domains without further testing."
    ),
}

ARTICLE_B = {
    "title": "Campus Wi-Fi Upgrade Improves Peak-Hour Throughput",
    "text": (
        "Following a campus-wide Wi-Fi access point upgrade, average peak-hour "
        "throughput in the library increased by 60%. The measurement was taken "
        "over two weeks post-upgrade using the network monitoring dashboard. "
        "The report does not include measurements from other buildings on campus, "
        "so it is unclear whether the improvement is uniform across campus."
    ),
}

SKILL_SPEC = {
    "name": "research_summary",
    "instructions": [
        "identify the single main claim",
        "list supporting evidence for that claim",
        "note at least one limitation (or 'not stated in source' if genuinely absent)",
        "write a 1-sentence undergraduate-level takeaway",
    ],
    "constraints": [
        "never present a hedged claim as unhedged fact",
        "never omit the limitation row, even if the source states none",
    ],
}


def apply_research_summary_skill(article):
    """A rule-based stand-in for an LLM applying the skill's instructions.
    In a real deployment this function's body would be an LLM call
    constrained by SKILL_SPEC; here the extraction is done directly so
    the workflow and output CONTRACT are runnable and testable."""
    text = article["text"]
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    claim = sentences[0]
    evidence = sentences[1] if len(sentences) > 1 else "not stated in source"
    limitation = next((s for s in sentences if "small" in s.lower()
                        or "does not include" in s.lower()
                        or "unclear" in s.lower()
                        or "may not generalize" in s.lower()), "not stated in source")
    takeaway = f"Undergraduate takeaway: {claim.strip().rstrip('.')} -- but verify before generalizing."

    return {
        "claim": claim,
        "evidence": evidence,
        "limitation": limitation,
        "takeaway": takeaway,
    }


def print_skill_output(article, output):
    print(f"\n--- {article['title']} ---")
    print(f"Claim:      {output['claim']}")
    print(f"Evidence:   {output['evidence']}")
    print(f"Limitation: {output['limitation']}")
    print(f"Takeaway:   {output['takeaway']}")


def reusability_check(output_a, output_b):
    keys_a, keys_b = set(output_a.keys()), set(output_b.keys())
    same_structure = keys_a == keys_b
    both_have_limitation = all(o["limitation"] != "" for o in (output_a, output_b))
    print("\n=== Reusability check ===")
    print(f"Same output structure across both inputs: {same_structure}")
    print(f"Limitation field populated in both outputs: {both_have_limitation}")
    print("Conclusion:", "SKILL IS REUSABLE" if same_structure and both_have_limitation
          else "SKILL NEEDS TIGHTER INSTRUCTIONS")



A1=True
A2=True

ARTICLE_C = {'title': 'Two competing claims', 'text': 'Cost falls by 20%. Accuracy increases by 12%. Accuracy was measured on 500 held-out cases. Accuracy may not generalize beyond this dataset.'}
ARTICLE_D = {'title': 'Unsupported assertion', 'text': 'Our agent is the best assistant ever.'}
def extended_summary(article):
    sentences = [s.strip() for s in article['text'].split('.') if s.strip()]
    claims = [s for s in sentences if not any(k in s.lower() for k in ('measured', 'may not', 'limitation', 'evaluation', 'measurement', 'authors note', 'report does not'))]
    evidence_sentences = [s for s in sentences if any(k in s.lower() for k in ('measured', 'evaluation used', 'measurement was'))]
    # Explicit lexical association for this classroom corpus; never invent evidence.
    scored = [(sum(bool(set(c.lower().split()) & set(e.lower().split())) for e in evidence_sentences), c) for c in claims]
    claim = max(scored, key=lambda item:item[0])[1] if scored else sentences[0]
    evidence = [s for s in evidence_sentences if set(claim.lower().split()) & set(s.lower().split())]
    limitation = next((s for s in sentences if any(k in s.lower() for k in ('small', 'may not', 'does not include', 'unclear'))), 'not stated in source')
    return {'claim': claim, 'evidence': '; '.join(evidence) or 'not stated in source', 'limitation': limitation,
            'selection_note': f'Selected most evidence-supported of {len(claims)} competing claims' if len(claims)>1 else 'Single claim identified',
            'takeaway': f'{claim}; inspect evidence and limits before generalizing.'}
def demo():
    for article in [ARTICLE_A, ARTICLE_B] + ([ARTICLE_C] if A1 else []) + ([ARTICLE_D] if A2 else []):
        r=extended_summary(article); print('Article:',article); print('Summary:', r)
        if article is ARTICLE_C:
            assert r['claim']=='Accuracy increases by 12%'
            assert 'competing claims' in r['selection_note']
        if article is ARTICLE_D:
            assert r['evidence']==r['limitation']=='not stated in source'
            print('No fabrication occurred: absent evidence and limitations are explicitly marked.')
    print('PASS: reusable extraction with explicit evidence limits')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Article: {'title': 'Retrieval-Augmented Generation Reduces Hallucination in Domain QA', 'text': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task. The evaluation used 200 held-out questions from a medical knowledge base. The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing.'}
Summary: {'claim': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task', 'evidence': 'The evaluation used 200 held-out questions from a medical knowledge base', 'limitation': 'The authors note the evaluation set was small and drawn from a single domain, so results may not generalize to other domains without further testing', 'selection_note': 'Single claim identified', 'takeaway': 'A recent benchmark study found that retrieval-augmented generation (RAG) reduced factual hallucination rates by 41% compared to a non-retrieval baseline on a domain-specific question-answering task; inspect evidence and limits before generalizing.'}
Article: {'title': 'Campus Wi-Fi Upgrade Improves Peak-Hour Throughput', 'text': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%. The measurement was taken over two weeks post-upgrade using the network monitoring dashboard. The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus.'}
Summary: {'claim': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%', 'evidence': 'The measurement was taken over two weeks post-upgrade using the network monitoring dashboard', 'limitation': 'The report does not include measurements from other buildings on campus, so it is unclear whether the improvement is uniform across campus', 'selection_note': 'Single claim identified', 'takeaway': 'Following a campus-wide Wi-Fi access point upgrade, average peak-hour throughput in the library increased by 60%; inspect evidence and limits before generalizing.'}
Article: {'title': 'Two competing claims', 'text': 'Cost falls by 20%. Accuracy increases by 12%. Accuracy was measured on 500 held-out cases. Accuracy may not generalize beyond this dataset.'}
Summary: {'claim': 'Accuracy increases by 12%', 'evidence': 'Accuracy was measured on 500 held-out cases', 'limitation': 'Accuracy may not generalize beyond this dataset', 'selection_note': 'Selected most evidence-supported of 2 competing claims', 'takeaway': 'Accuracy increases by 12%; inspect evidence and limits before generalizing.'}
Article: {'title': 'Unsupported assertion', 'text': 'Our agent is the best assistant ever.'}
Summary: {'claim': 'Our agent is the best assistant ever', 'evidence': 'not stated in source', 'limitation': 'not stated in source', 'selection_note': 'Single claim identified', 'takeaway': 'Our agent is the best assistant ever; inspect evidence and limits before generalizing.'}
No fabrication occurred: absent evidence and limitations are explicitly marked.
PASS: reusable extraction with explicit evidence limits
```


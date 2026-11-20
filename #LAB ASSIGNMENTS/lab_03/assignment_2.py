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

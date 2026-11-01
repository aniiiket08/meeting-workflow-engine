"""
Phase 2 / Correctness Fix 1.7 — Expanded Memory / Retrieval Benchmark
Tests BM25-style MemoryStore with both original queries and unseen test cases.
Measures Precision@1, Precision@3, Recall@3, and latency.
"""
import json
import statistics
import sys
import time

sys.path.insert(0, "backend")

from app.memory.vector_store import MemoryStore

store = MemoryStore()
print(f"Documents loaded: {len(store.documents)}")
print(f"Implementation: BM25-style token frequency + IDF + recency ranking (Keyword-based)")
print()

# Labelled test cases:
# Explicitly partitioned into:
# 1. 5 Original queries (labelled: "tuned on 5 queries")
# 2. 7 Unseen queries (domain variations, paraphrases, and irrelevant noise)
TEST_CASES = [
    # ── Original 5 Queries (tuned set) ───────────────────────────────────────
    {
        "query": "GPU cluster budget procurement",
        "expected_doc_ids": [101],
        "expected_keywords": ["gpu", "budget", "infrastructure"],
        "expect_results": True,
        "subset": "tuned_on_5_queries",
    },
    {
        "query": "room scheduling reservation booking",
        "expected_doc_ids": [105],
        "expected_keywords": ["room", "scheduling", "reservation", "booking", "operations"],
        "expect_results": True,
        "subset": "tuned_on_5_queries",
    },
    {
        "query": "fee payment student",
        "expected_doc_ids": [],
        "expected_keywords": ["fee", "student", "payment"],
        "expect_results": False,
        "subset": "tuned_on_5_queries",
    },
    {
        "query": "research publication project",
        "expected_doc_ids": [],
        "expected_keywords": ["research", "publication", "project"],
        "expect_results": False,
        "subset": "tuned_on_5_queries",
    },
    {
        "query": "xyznonexistentterm000 abc999",
        "expected_doc_ids": [],
        "expected_keywords": [],
        "expect_results": False,
        "subset": "tuned_on_5_queries",
    },

    # ── 7 Unseen Queries (held-out evaluation set) ────────────────────────────
    {
        "query": "student privacy and personal data redaction policy",
        "expected_doc_ids": [104],
        "expected_keywords": ["pii", "redaction", "security", "transcript"],
        "expect_results": True,
        "subset": "unseen_evaluation",
    },
    {
        "query": "syllabus update for artificial intelligence safety unit",
        "expected_doc_ids": [102],
        "expected_keywords": ["curriculum", "ai", "syllabus", "ethics", "cs402"],
        "expect_results": True,
        "subset": "unseen_evaluation",
    },
    {
        "query": "grading rubric weights and capstone deliverables",
        "expected_doc_ids": [103],
        "expected_keywords": ["capstone", "rubric", "grading"],
        "expect_results": True,
        "subset": "unseen_evaluation",
    },
    {
        "query": "conflict prevention for seminar hall reservations",
        "expected_doc_ids": [105],
        "expected_keywords": ["room", "conflict", "double-booking", "scheduling"],
        "expect_results": True,
        "subset": "unseen_evaluation",
    },
    {
        "query": "procuring H100 hardware accelerator units",
        "expected_doc_ids": [101],
        "expected_keywords": ["gpu", "h100", "purchases", "hardware"],
        "expect_results": True,
        "subset": "unseen_evaluation",
    },
    {
        "query": "quantum computing cryogenic cooling dilution refrigerator",
        "expected_doc_ids": [],
        "expected_keywords": [],
        "expect_results": False,
        "subset": "unseen_evaluation",
    },
    {
        "query": "campus cafeteria meal plans and dining hall hours",
        "expected_doc_ids": [],
        "expected_keywords": [],
        "expect_results": False,
        "subset": "unseen_evaluation",
    },
]

latencies_ms: list[float] = []
eval_rows = []

for case in TEST_CASES:
    t0 = time.perf_counter()
    hits = store.search(case["query"], top_k=3)
    elapsed = (time.perf_counter() - t0) * 1000
    latencies_ms.append(elapsed)

    hit_doc_ids = [doc.get("meeting_id") for doc in hits if doc.get("meeting_id")]
    
    # Precision@1: Top result matches expected doc (or if expected empty, hits is empty)
    p_at_1 = 0.0
    if not case["expected_doc_ids"]:
        p_at_1 = 1.0 if not hits else 0.0
    else:
        p_at_1 = 1.0 if hits and hits[0].get("meeting_id") in case["expected_doc_ids"] else 0.0

    # Recall@3: Any top 3 results contain the target doc
    r_at_3 = 0.0
    if not case["expected_doc_ids"]:
        r_at_3 = 1.0 if not hits else 0.0
    else:
        found = any(did in hit_doc_ids for did in case["expected_doc_ids"])
        r_at_3 = 1.0 if found else 0.0

    # Precision@3: Fraction of top-3 results that are relevant
    p_at_3 = 0.0
    if not case["expected_doc_ids"]:
        p_at_3 = 1.0 if not hits else 0.0
    else:
        relevant_in_top3 = sum(1 for did in hit_doc_ids if did in case["expected_doc_ids"])
        p_at_3 = (relevant_in_top3 / min(len(hits), 3)) if hits else 0.0

    eval_rows.append({
        "query": case["query"],
        "subset": case["subset"],
        "latency_ms": round(elapsed, 2),
        "result_count": len(hits),
        "p_at_1": p_at_1,
        "p_at_3": round(p_at_3, 3),
        "r_at_3": r_at_3,
        "expected_doc_ids": case["expected_doc_ids"],
        "returned_doc_ids": hit_doc_ids,
    })

# Compute metrics partitioned by subset
def compute_subset_metrics(rows):
    p1 = statistics.mean(r["p_at_1"] for r in rows) if rows else 0.0
    p3 = statistics.mean(r["p_at_3"] for r in rows) if rows else 0.0
    r3 = statistics.mean(r["r_at_3"] for r in rows) if rows else 0.0
    lat = [r["latency_ms"] for r in rows]
    return {
        "sample_size": len(rows),
        "p_at_1": round(p1, 3),
        "p_at_3": round(p3, 3),
        "r_at_3": round(r3, 3),
        "latency_mean_ms": round(statistics.mean(lat), 3) if lat else 0.0,
        "latency_p50_ms": round(statistics.median(lat), 3) if lat else 0.0,
        "latency_p95_ms": round(sorted(lat)[int(len(lat) * 0.95)], 3) if lat else 0.0,
    }

tuned_rows = [r for r in eval_rows if r["subset"] == "tuned_on_5_queries"]
unseen_rows = [r for r in eval_rows if r["subset"] == "unseen_evaluation"]

overall_metrics = {
    "documents_loaded": len(store.documents),
    "implementation": "BM25-style token frequency + IDF + recency ranking (Keyword-based)",
    "vector_store_active": False,
    "vector_store_note": "ChromaDB module exists in repository but active retriever is BM25-based MemoryStore",
    "tuned_on_5_queries": compute_subset_metrics(tuned_rows),
    "unseen_evaluation_7_queries": compute_subset_metrics(unseen_rows),
    "combined_12_queries": compute_subset_metrics(eval_rows),
    "eval_rows": eval_rows,
}

print("=" * 60)
print("EXPANDED MEMORY RETRIEVAL RESULTS (JSON)")
print("=" * 60)
print(json.dumps(overall_metrics, indent=2))

with open("evaluation/baseline_memory.json", "w") as f:
    json.dump(overall_metrics, f, indent=2)
print("\nSaved -> evaluation/baseline_memory.json")

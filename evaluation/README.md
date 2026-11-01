# Automated Benchmark Runner & Instructions

This directory contains standalone, reproducible Python and Locust scripts designed to evaluate the **Meeting Organizer Agent** across all system tiers.

---

## 1. Prerequisites

Ensure dependencies and virtual environment are initialized:

```bash
# From repository root
.venv\Scripts\activate
pip install httpx locust pytest
```

---

## 2. Benchmark Suite Scripts

### 2.1 Backend API Latency & Health
Measures cold vs warm latency percentiles, status codes, and payload bytes:
```bash
python evaluation/bench_api.py
```
*Output: Saves raw measurements to `evaluation/baseline_api.json`.*

### 2.2 Memory Store Retrieval Quality
Evaluates BM25 keyword matching, latency, precision, and recall against labelled query test sets:
```bash
python evaluation/bench_memory.py
```
*Output: Saves metrics to `evaluation/baseline_memory.json`.*

### 2.3 Model Context Protocol (MCP) Tools
Tests room search, boundary conditions, and double-booking rejection:
```bash
python evaluation/bench_mcp.py
```
*Output: Saves tool timing to `evaluation/baseline_mcp.json`.*

### 2.4 AI Quality & Transcript Grounding
Instruments live Google Gemini calls, calculating Action-Item Precision, Recall, F1, Grounding Rate, and Token counts:
```bash
python evaluation/bench_llm_quality.py
```
*Output: Saves evaluations to `evaluation/baseline_llm_quality.json`.*

### 2.5 LangGraph Multi-Agent Workflow
Executes the full 9-node meeting lifecycle with human approval gates:
```bash
python evaluation/bench_workflow.py
```
*Output: Saves node timing to `evaluation/workflow_results.json`.*

### 2.6 Frontend Production Bundle Analysis
Measures bundle asset sizes, chunk splits, and compression:
```bash
python evaluation/bench_frontend.py
```
*Output: Saves asset breakdown to `evaluation/frontend_bundle.json`.*

### 2.7 Load & Stress Testing (Locust)
Simulates realistic concurrent user workloads against the live API:
```bash
# 1-User Smoke Test (20s)
locust -f evaluation/locustfile.py --headless -u 1 -r 1 --run-time 20s --host http://127.0.0.1:8765 --csv evaluation/load_1u

# 5-User Baseline Test (20s)
locust -f evaluation/locustfile.py --headless -u 5 -r 2 --run-time 20s --host http://127.0.0.1:8765 --csv evaluation/load_5u

# 10-User Moderate Test (20s)
locust -f evaluation/locustfile.py --headless -u 10 -r 2 --run-time 20s --host http://127.0.0.1:8765 --csv evaluation/load_10u

# 20-User Stress Test (20s)
locust -f evaluation/locustfile.py --headless -u 20 -r 4 --run-time 20s --host http://127.0.0.1:8765 --csv evaluation/load_20u
```

---

## 3. One-Click Automated Run

To execute all benchmarks sequentially and compile the final summary:

```bash
# Run complete test harness
python -c "
import subprocess
scripts = [
    'evaluation/bench_api.py',
    'evaluation/bench_memory.py',
    'evaluation/bench_mcp.py',
    'evaluation/bench_llm_quality.py',
    'evaluation/bench_workflow.py',
    'evaluation/bench_frontend.py'
]
for s in scripts:
    print('Running', s)
    subprocess.run(['.venv/Scripts/python.exe', s], check=True)
print('All benchmarks completed successfully.')
"
```


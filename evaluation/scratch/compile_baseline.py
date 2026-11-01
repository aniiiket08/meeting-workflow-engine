import json

with open("evaluation/baseline_api.json") as f:
    api = json.load(f)

with open("evaluation/baseline_db.json") as f:
    db = json.load(f)

with open("evaluation/baseline_memory.json") as f:
    memory = json.load(f)

with open("evaluation/baseline_mcp.json") as f:
    mcp = json.load(f)

with open("evaluation/baseline_llm_quality.json") as f:
    llm = json.load(f)

with open("evaluation/frontend_bundle.json") as f:
    frontend = json.load(f)

with open("evaluation/workflow_results.json") as f:
    workflow = json.load(f)

# Load locust 10u stats
locust_summary = {
    "1u_smoke_rps": 0.87,
    "1u_smoke_p50_ms": 4.0,
    "5u_load_rps": 4.21,
    "5u_load_p50_ms": 3.0,
    "10u_load_rps": 7.71,
    "10u_load_p50_ms": 4.0,
    "10u_load_p95_ms": 260.0,
    "20u_stress_rps": 15.64,
    "20u_stress_p50_ms": 4.0,
    "20u_stress_p95_ms": 260.0,
    "total_requests_20u": 306,
    "error_rate_20u_percent": 0.0
}

baseline_master = {
    "evaluation_timestamp": "2026-11-01T06:26:00Z",
    "environment": {
        "os": "Windows 11",
        "python": "3.12.10",
        "node": "v20+",
        "model": "gemini-3.1-flash-lite",
        "database": "SQLite (QueuePool, WAL mode compatible)",
        "frontend": "React + Vite 5.4.21 + Tailwind CSS"
    },
    "api_baseline": api,
    "database_queries": db,
    "memory_retrieval": memory,
    "mcp_tools": mcp,
    "llm_and_quality": llm,
    "frontend_assets": frontend,
    "agent_workflow": workflow,
    "load_testing": locust_summary
}

with open("evaluation/baseline_results.json", "w") as f:
    json.dump(baseline_master, f, indent=2)

print("Saved -> evaluation/baseline_results.json")


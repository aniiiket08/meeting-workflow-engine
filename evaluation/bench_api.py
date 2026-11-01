"""
Phase 2 — API Baseline Latency Benchmark
Runs 10 iterations per endpoint, reports cold, warm p50/p90, errors.
"""
import json
import statistics
import sys
import time

import httpx

sys.path.insert(0, "backend")

BASE = "http://127.0.0.1:8765"
results: dict = {}


def measure(label: str, method: str, url: str, n: int = 10, **kwargs) -> dict:
    latencies = []
    statuses = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            resp = httpx.request(method, url, timeout=5.0, **kwargs)
            statuses.append(resp.status_code)
        except Exception:
            statuses.append(0)
        latencies.append((time.perf_counter() - t) * 1000)
    errors = sum(1 for s in statuses if s == 0 or s >= 400)
    warm = sorted(latencies[1:]) if len(latencies) > 1 else latencies
    rec = {
        "cold_ms": round(latencies[0], 2),
        "p50_ms": round(statistics.median(warm), 2),
        "p90_ms": round(warm[int(len(warm) * 0.9)], 2) if warm else 0,
        "min_ms": round(min(warm), 2),
        "max_ms": round(max(warm), 2),
        "mean_ms": round(statistics.mean(warm), 2),
        "error_count": errors,
        "status_codes": statuses,
        "n": n,
    }
    results[label] = rec
    return rec


# ── No-auth endpoints ────────────────────────────────────────────────────────
for label, path in [("GET /health", "/health"), ("GET /", "/")]:
    r = measure(label, "GET", f"{BASE}{path}")
    print(f"{label}: cold={r['cold_ms']}ms  p50={r['p50_ms']}ms  p90={r['p90_ms']}ms  err={r['error_count']}")

# ── Login ────────────────────────────────────────────────────────────────────
t0 = time.perf_counter()
try:
    login_resp = httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": "chairman", "password": "changeme"},
        timeout=5.0,
    )
    login_ms = (time.perf_counter() - t0) * 1000
    token = login_resp.json().get("access_token", "")
    print(
        f"POST /auth/login: {login_ms:.1f}ms  status={login_resp.status_code}"
        f"  token={'OK' if token else 'MISSING'}"
    )
    results["POST /auth/login"] = {
        "latency_ms": round(login_ms, 2),
        "status": login_resp.status_code,
        "got_token": bool(token),
    }
except Exception as exc:
    print("Login failed:", exc)
    token = ""

# ── Wrong-password (401 check) ───────────────────────────────────────────────
try:
    bad_resp = httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": "chairman", "password": "wrongpassword"},
        timeout=5.0,
    )
    print(f"POST /auth/login (bad pwd): status={bad_resp.status_code}  expected=401")
    results["POST /auth/login (bad pwd)"] = {"status": bad_resp.status_code}
except Exception as exc:
    print("Bad-pwd test failed:", exc)

# ── Authenticated endpoints ──────────────────────────────────────────────────
if token:
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        ("GET /auth/me", "GET", "/api/v1/auth/me"),
        ("GET /meetings", "GET", "/api/v1/meetings"),
        ("GET /rooms", "GET", "/api/v1/rooms"),
        ("GET /actions", "GET", "/api/v1/actions"),
        ("GET /schedule", "GET", "/api/v1/schedule"),
        ("GET /agendas", "GET", "/api/v1/agendas"),
    ]
    for label, method, path in endpoints:
        r = measure(label, method, f"{BASE}{path}", headers=headers)
        print(
            f"{label}: cold={r['cold_ms']}ms  p50={r['p50_ms']}ms"
            f"  p90={r['p90_ms']}ms  err={r['error_count']}"
        )

    # ── RBAC checks ─────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    rbac_resp = httpx.get(f"{BASE}/api/v1/auth/chairman-only", headers=headers, timeout=5.0)
    rbac_ms = (time.perf_counter() - t0) * 1000
    print(f"GET /chairman-only (chairman): {rbac_ms:.1f}ms  status={rbac_resp.status_code}  expected=200")
    results["GET /auth/chairman-only (chairman)"] = {"status": rbac_resp.status_code, "latency_ms": round(rbac_ms, 2)}

    # Login as teacher and check RBAC
    try:
        teacher_resp = httpx.post(
            f"{BASE}/api/v1/auth/login",
            json={"username": "teacher", "password": "changeme"},
            timeout=5.0,
        )
        teacher_token = teacher_resp.json().get("access_token", "")
        if teacher_token:
            t0 = time.perf_counter()
            denied = httpx.get(
                f"{BASE}/api/v1/auth/chairman-only",
                headers={"Authorization": f"Bearer {teacher_token}"},
                timeout=5.0,
            )
            denied_ms = (time.perf_counter() - t0) * 1000
            print(f"GET /chairman-only (teacher): {denied_ms:.1f}ms  status={denied.status_code}  expected=403")
            results["GET /auth/chairman-only (teacher=denied)"] = {
                "status": denied.status_code,
                "latency_ms": round(denied_ms, 2),
            }
    except Exception as exc:
        print("Teacher RBAC check failed:", exc)

    # ── Payload size check ───────────────────────────────────────────────────
    for path, label in [("/api/v1/meetings", "meetings"), ("/api/v1/rooms", "rooms")]:
        resp = httpx.get(f"{BASE}{path}", headers=headers, timeout=5.0)
        body_bytes = len(resp.content)
        results.setdefault(f"GET /{label}", {})["payload_bytes"] = body_bytes
        print(f"GET /{label} payload: {body_bytes} bytes")

print()
print("=" * 60)
print("BASELINE API RESULTS (JSON)")
print("=" * 60)
print(json.dumps(results, indent=2))

# Save for deliverables
with open("evaluation/baseline_api.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved -> evaluation/baseline_api.json")


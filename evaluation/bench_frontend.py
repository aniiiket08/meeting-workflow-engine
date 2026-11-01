import os
import json
from pathlib import Path

dist_dir = Path("frontend/dist")
assets_dir = dist_dir / "assets"

assets = []
total_bytes = 0
for f in assets_dir.glob("*"):
    size = f.stat().st_size
    total_bytes += size
    assets.append({
        "name": f.name,
        "size_kb": round(size / 1024, 2),
        "size_bytes": size,
        "type": "css" if f.suffix == ".css" else "js" if f.suffix == ".js" else f.suffix
    })

index_html_size = (dist_dir / "index.html").stat().st_size if (dist_dir / "index.html").exists() else 0

report = {
    "dist_exists": dist_dir.exists(),
    "index_html_bytes": index_html_size,
    "total_bundle_size_kb": round((total_bytes + index_html_size) / 1024, 2),
    "assets": sorted(assets, key=lambda x: x["size_bytes"], reverse=True),
    "modules_transformed": 1509,
    "build_tool": "Vite 5.4.21 + TypeScript 5.6",
    "largest_asset": max(assets, key=lambda x: x["size_bytes"])["name"] if assets else None
}

print(json.dumps(report, indent=2))
with open("evaluation/frontend_bundle.json", "w") as f:
    json.dump(report, f, indent=2)
print("Saved -> evaluation/frontend_bundle.json")


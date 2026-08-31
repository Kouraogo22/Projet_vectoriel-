"""Audit local des documents indexés par catégorie via l'API FastAPI."""

from collections import Counter, defaultdict
from pathlib import Path
import json
import os
import sys
import urllib.request


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
OUTPUT = Path("evaluation/results/qdrant_category_audit.json")


def main() -> None:
    with urllib.request.urlopen(f"{API_URL}/documents", timeout=30) as response:
        documents = json.load(response)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for document in documents:
        grouped[document.get("category") or "Sans catégorie"].append(document)

    report = {
        "total_documents": len(documents),
        "categories": {
            category: {
                "count": len(items),
                "titles": sorted(item["title"] for item in items),
            }
            for category, items in sorted(grouped.items())
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = Counter(document.get("category") or "Sans catégorie" for document in documents)
    print(f"Documents indexés : {len(documents)}")
    for category, count in sorted(counts.items()):
        print(f"- {category} : {count}")
    print(f"Rapport : {OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Audit impossible : {exc}", file=sys.stderr)
        raise SystemExit(1)

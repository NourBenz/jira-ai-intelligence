"""Run the repeatable RAG retrieval evaluation against the local API."""

import argparse
import json
from pathlib import Path

import requests

from app.rag.evaluation import evaluate_rankings, load_retrieval_cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evaluation/rag_retrieval_cases.json"),
    )
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--min-mrr", type=float, default=0.5)
    args = parser.parse_args()

    cases = load_retrieval_cases(args.cases)
    rankings: dict[str, list[str]] = {}
    for case in cases:
        response = requests.post(
            f"{args.base_url.rstrip('/')}/api/rag/projects/{case.project_key}/search",
            json={"query": case.query, "top_k": case.top_k},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        issue_keys = [
            str(result["metadata"]["issue_key"])
            for result in payload["results"]
            if result.get("metadata", {}).get("issue_key")
        ]
        rankings[case.id] = list(dict.fromkeys(issue_keys))

    metrics = evaluate_rankings(cases, rankings)
    print(json.dumps(metrics, indent=2))
    passes = (
        metrics["recall_at_k"] >= args.min_recall
        and metrics["mean_reciprocal_rank"] >= args.min_mrr
    )
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())

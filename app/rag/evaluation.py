"""Deterministic retrieval-quality metrics for Phase 6 evaluation cases."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RetrievalCase:
    id: str
    project_key: str
    query: str
    relevant_issue_keys: frozenset[str]
    top_k: int


def load_retrieval_cases(path: Path) -> list[RetrievalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Retrieval evaluation data must be a non-empty list.")

    cases = []
    for item in payload:
        relevant = frozenset(str(key) for key in item["relevant_issue_keys"])
        top_k = int(item.get("top_k", 10))
        if not relevant or not 1 <= top_k <= 20:
            raise ValueError("Each retrieval case needs relevant keys and top_k 1..20.")
        cases.append(
            RetrievalCase(
                id=str(item["id"]),
                project_key=str(item["project_key"]),
                query=str(item["query"]),
                relevant_issue_keys=relevant,
                top_k=top_k,
            )
        )
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Retrieval evaluation case identifiers must be unique.")
    return cases


def evaluate_rankings(
    cases: list[RetrievalCase],
    ranked_issue_keys: dict[str, list[str]],
) -> dict[str, Any]:
    if not cases:
        raise ValueError("At least one retrieval case is required.")

    details = []
    reciprocal_rank_total = 0.0
    hit_count = 0
    for case in cases:
        ranking = ranked_issue_keys.get(case.id, [])[: case.top_k]
        first_relevant_rank = next(
            (
                index
                for index, issue_key in enumerate(ranking, start=1)
                if issue_key in case.relevant_issue_keys
            ),
            None,
        )
        hit = first_relevant_rank is not None
        reciprocal_rank = 1.0 / first_relevant_rank if first_relevant_rank else 0.0
        hit_count += int(hit)
        reciprocal_rank_total += reciprocal_rank
        details.append(
            {
                "id": case.id,
                "hit": hit,
                "first_relevant_rank": first_relevant_rank,
                "reciprocal_rank": round(reciprocal_rank, 4),
                "returned_issue_keys": ranking,
            }
        )

    total = len(cases)
    return {
        "cases": total,
        "hits": hit_count,
        "recall_at_k": round(hit_count / total, 4),
        "mean_reciprocal_rank": round(reciprocal_rank_total / total, 4),
        "details": details,
    }

from pathlib import Path

import pytest

from app.rag.evaluation import (
    RetrievalCase,
    evaluate_rankings,
    load_retrieval_cases,
)


def test_phase_six_retrieval_cases_are_valid_and_repeatable():
    path = Path("evaluation/rag_retrieval_cases.json")

    first = load_retrieval_cases(path)
    second = load_retrieval_cases(path)

    assert first == second
    assert len(first) == 5
    assert {case.project_key for case in first} == {"T1"}
    assert all(case.relevant_issue_keys for case in first)


def test_retrieval_metrics_measure_recall_and_reciprocal_rank():
    cases = [
        RetrievalCase("first", "T1", "query one", frozenset({"T1-1"}), 3),
        RetrievalCase("second", "T1", "query two", frozenset({"T1-2"}), 3),
    ]

    result = evaluate_rankings(
        cases,
        {
            "first": ["T1-9", "T1-1", "T1-8"],
            "second": ["T1-7", "T1-6", "T1-5"],
        },
    )

    assert result["hits"] == 1
    assert result["recall_at_k"] == 0.5
    assert result["mean_reciprocal_rank"] == 0.25
    assert result["details"][0]["first_relevant_rank"] == 2
    assert result["details"][1]["first_relevant_rank"] is None


def test_retrieval_evaluation_rejects_empty_case_list():
    with pytest.raises(ValueError):
        evaluate_rankings([], {})

"""Deterministic routing and formatting for structured project questions."""

import re
from difflib import SequenceMatcher
from typing import Literal

ISSUE_KEY_PATTERN = re.compile(r"(?<![A-Z0-9_])([A-Z][A-Z0-9_]*-\d+)(?![A-Z0-9_])", re.I)
WORD_PATTERN = re.compile(r"[a-z0-9]+")
StructuredIssueField = Literal["priority", "status", "assignee", "issue_type"]
SEMANTIC_SEARCH_STOP_WORDS = {
    "a",
    "about",
    "abt",
    "an",
    "any",
    "discuss",
    "discusses",
    "find",
    "for",
    "issue",
    "issues",
    "mention",
    "mentions",
    "related",
    "search",
    "task",
    "tasks",
    "ticket",
    "tickets",
    "to",
    "talk",
    "talks",
    "what",
    "which",
}

STRUCTURED_FIELD_ALIASES: dict[StructuredIssueField, tuple[str, ...]] = {
    "priority": ("priority", "priorities"),
    "status": (
        "status",
        "statuses",
        "workflow state",
        "to do",
        "in progress",
        "in review",
        "done",
    ),
    "assignee": ("assignee", "assigned to", "owner", "owned by"),
    "issue_type": (
        "issue type",
        "ticket type",
        "work item type",
        "bug",
        "bugs",
        "story",
        "stories",
        "epic",
        "epics",
        "subtask",
        "subtasks",
    ),
}


def extract_issue_keys(question: str) -> list[str]:
    """Return unique, normalized Jira issue keys explicitly named by the user."""
    keys: list[str] = []
    for match in ISSUE_KEY_PATTERN.finditer(question):
        key = match.group(1).upper()
        if key not in keys:
            keys.append(key)
    return keys


def requires_semantic_issue_search(question: str) -> bool:
    """Identify requests whose desired output is a set of semantically related issues."""
    normalized = " ".join(question.casefold().split())
    search_terms = (
        "mention",
        "mentions",
        "discuss",
        "discusses",
        "related to",
        "find ticket",
        "find tickets",
        "find issue",
        "find issues",
        "search for",
        "talk about",
        "talk abt",
    )
    return any(term in normalized for term in search_terms)


def semantic_search_terms(question: str) -> set[str]:
    """Extract meaningful words used to reject semantically plausible false positives."""
    return {
        word
        for word in WORD_PATTERN.findall(question.casefold())
        if len(word) >= 2 and word not in SEMANTIC_SEARCH_STOP_WORDS
    }


def requires_unassigned_analytics(question: str) -> bool:
    """Recognize informal questions about work without an assignee."""
    normalized = " ".join(question.casefold().split())
    return any(
        phrase in normalized
        for phrase in (
            "unassigned",
            "no assignee",
            "without an assignee",
            "without assignee",
            "nobody is assigned",
            "nobody assigned",
            "not assigned to anyone",
        )
    )


def requires_workload_analytics(question: str) -> bool:
    """Recognize informal questions about assignment concentration."""
    normalized = " ".join(question.casefold().split())
    return any(
        phrase in normalized
        for phrase in (
            "workload",
            "too much work",
            "most work",
            "most tasks",
            "most tickets",
            "overloaded",
            "who has the most",
            "whos got too much",
            "who's got too much",
        )
    )


def requires_comment_analytics(question: str) -> bool:
    """Recognize requests asking which synchronized issues contain comments."""
    normalized = " ".join(question.casefold().split())
    words = WORD_PATTERN.findall(normalized)
    mentions_comments = any(
        word.startswith("comment")
        or (len(word) >= 6 and SequenceMatcher(None, word, "comments").ratio() >= 0.82)
        for word in words
    )
    asks_for_issue_set = any(
        phrase in normalized
        for phrase in (
            "which issue",
            "which ticket",
            "what issue",
            "what ticket",
            "issues have",
            "tickets have",
            "any issue",
            "any ticket",
            "how many issue",
            "how many ticket",
            "list issue",
            "list ticket",
        )
    )
    return mentions_comments and asks_for_issue_set


def requires_sprint_analytics(question: str) -> bool:
    """Identify sprint list/count questions that semantic retrieval must not answer."""
    normalized = " ".join(question.casefold().split())
    mentions_sprint = any(
        term in normalized for term in ("sprint", "sprints", "spint", "spints", "split", "splits")
    )
    asks_for_structure = any(
        term in normalized
        for term in (
            "how many",
            "count",
            "number of",
            "different sprint",
            "list sprint",
            "which sprint",
            "what sprint",
        )
    )
    return mentions_sprint and asks_for_structure


def structured_issue_field(question: str) -> StructuredIssueField | None:
    """Recognize an issue-field filtering question, including small field-name typos."""
    normalized = " ".join(question.casefold().split())
    for field, aliases in STRUCTURED_FIELD_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return field

    question_words = WORD_PATTERN.findall(normalized)
    for word in question_words:
        if len(word) < 5:
            continue
        for field, aliases in STRUCTURED_FIELD_ALIASES.items():
            single_word_aliases = [alias for alias in aliases if " " not in alias]
            if any(
                SequenceMatcher(None, word, alias).ratio() >= 0.82 for alias in single_word_aliases
            ):
                return field
    return None


def match_structured_value(question: str, values: list[str]) -> str | None:
    """Match a requested value against real project values without inventing one."""
    normalized_question = " ".join(question.casefold().split())
    compact_question = "".join(WORD_PATTERN.findall(normalized_question))
    question_words = WORD_PATTERN.findall(normalized_question)
    ranked: list[tuple[float, str]] = []

    for value in sorted(set(values), key=str.casefold):
        normalized_value = " ".join(value.casefold().split())
        value_words = WORD_PATTERN.findall(normalized_value)
        if not value_words:
            continue

        has_exact_word_sequence = any(
            question_words[start : start + len(value_words)] == value_words
            for start in range(0, len(question_words) - len(value_words) + 1)
        )
        if has_exact_word_sequence:
            score = 1.0
        elif "".join(value_words) in compact_question:
            score = 0.97
        else:
            score = 0.0
            window_size = len(value_words)
            for size in range(max(1, window_size - 1), window_size + 2):
                for start in range(0, len(question_words) - size + 1):
                    candidate = " ".join(question_words[start : start + size])
                    score = max(score, SequenceMatcher(None, normalized_value, candidate).ratio())
        if score >= 0.82:
            ranked.append((score, value))

    ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
    if not ranked:
        return None
    if ranked[0][0] == 1.0:
        return ranked[0][1]
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.05:
        return None
    return ranked[0][1]


def format_sprint_summary(summary: dict) -> str:
    """Format stored sprint facts without using a language model."""
    total = int(summary["total_sprints"])
    noun = "sprint" if total == 1 else "sprints"
    if not summary["sprints"]:
        return f"Project {summary['project_key']} has no synchronized sprints."
    details = [
        (
            f"{sprint['name']} ({sprint['state']}, "
            f"{sprint['issue_count']} issue"
            f"{'s' if sprint['issue_count'] != 1 else ''})"
        )
        for sprint in summary["sprints"]
    ]
    return f"Project {summary['project_key']} has {total} {noun}: " + "; ".join(details) + "."

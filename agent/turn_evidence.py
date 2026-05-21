"""Per-turn execution evidence helpers.

This keeps audit data cheap and deterministic.  Logs should not need full
session JSONL inspection to answer "did this turn actually use tools?".
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _get_mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _tool_call_id(tool_call: Any) -> str:
    raw = _get_mapping_value(tool_call, "id") or _get_mapping_value(tool_call, "tool_call_id")
    return str(raw or "")


def _tool_call_name(tool_call: Any) -> str:
    function = _get_mapping_value(tool_call, "function")
    raw = _get_mapping_value(function, "name")
    return str(raw or "").strip()


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _guard_metadata(commitment_guard: Any) -> dict[str, Any] | None:
    if commitment_guard is None:
        return None
    if isinstance(commitment_guard, Mapping):
        return dict(commitment_guard)
    to_metadata = getattr(commitment_guard, "to_metadata", None)
    if callable(to_metadata):
        try:
            metadata = to_metadata()
            if isinstance(metadata, Mapping):
                return dict(metadata)
        except Exception:
            return {"action": "unknown"}
    return {"action": "unknown"}


def collect_turn_evidence(
    messages: Iterable[Mapping[str, Any]],
    *,
    current_turn_user_idx: int,
    commitment_guard: Any = None,
) -> dict[str, Any]:
    """Collect tool evidence from messages after the current user turn."""

    tool_call_count = 0
    tool_result_count = 0
    tool_names: list[str] = []
    tool_result_names: list[str] = []
    tool_name_by_call_id: dict[str, str] = {}

    for idx, msg in enumerate(messages):
        if idx <= current_turn_user_idx or not isinstance(msg, Mapping):
            continue

        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                tool_call_count += 1
                name = _tool_call_name(tool_call)
                call_id = _tool_call_id(tool_call)
                if call_id and name:
                    tool_name_by_call_id[call_id] = name
                _append_unique(tool_names, name)
        elif tool_calls:
            tool_call_count += 1

        if msg.get("role") == "tool":
            tool_result_count += 1
            name = str(
                msg.get("name")
                or msg.get("tool_name")
                or tool_name_by_call_id.get(str(msg.get("tool_call_id") or ""))
                or "unknown"
            ).strip()
            _append_unique(tool_result_names, name)
            _append_unique(tool_names, name if name != "unknown" else "")

    guard = _guard_metadata(commitment_guard)
    evidence = {
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count,
        "tool_names": tool_names,
        "tool_result_names": tool_result_names,
        "has_tool_evidence": tool_call_count > 0 or tool_result_count > 0,
    }
    if guard:
        evidence["commitment_guard"] = guard
    return evidence


def format_turn_evidence_for_log(evidence: Mapping[str, Any] | None) -> str:
    """Return a compact single-field representation for gateway logs."""

    if not isinstance(evidence, Mapping):
        return "tools=0 results=0"

    tool_calls = int(evidence.get("tool_call_count") or 0)
    tool_results = int(evidence.get("tool_result_count") or 0)
    names = evidence.get("tool_names") or []
    if isinstance(names, (list, tuple)):
        name_text = ",".join(str(name) for name in names[:8] if str(name))
        if len(names) > 8:
            name_text += ",..."
    else:
        name_text = str(names)

    parts = [f"tools={tool_calls}", f"results={tool_results}"]
    if name_text:
        parts.append(f"names={name_text}")

    guard = evidence.get("commitment_guard")
    if isinstance(guard, Mapping):
        action = str(guard.get("action") or "").strip()
        reason = str(guard.get("reason") or "").strip()
        if action:
            parts.append(f"guard={action}")
        if reason:
            parts.append(f"guard_reason={reason}")

    return " ".join(parts)

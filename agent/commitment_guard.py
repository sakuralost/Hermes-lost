"""Runtime guard for tool-free execution promises.

The system prompt can ask a model not to claim future/background work, but
that is still a soft constraint.  This module gives the agent loop a small
deterministic check: if a final text response says the agent has started or
will later report on work, the current turn must contain execution evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence


_COMMITMENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(?:i'?m|i am|i will|i'?ll|i shall|i can now)\s+"
        r"(?:start|begin|continue|run|execute|research|investigate|look into|work on)\b",
        r"\b(?:i will|i'?ll|i am going to)\s+(?:use|call|run)\s+"
        r"(?:tools?|web|browser|search|x search|terminal|cron)\b",
        r"\b(?:i'?m|i am)\s+(?:working|researching|investigating|checking|searching)\b",
        r"\b(?:will|i'?ll)\s+(?:get back|report back|send|return|notify)\b"
        r".{0,80}\b(?:result|report|findings|summary|answer)\b",
        r"\b(?:after|once)\s+(?:the\s+)?(?:research|check|search|run|task)\b"
        r".{0,80}\b(?:complete|done|finishes|is finished)\b",
        r"(?:我|这边)?(?:现在|马上|这就|接下来|已经)?\s*"
        r"(?:开始|继续|执行|处理|调研|搜索|检查|跑|创建|添加)\b",
        r"(?:我|这边)?(?:正在|已经开始|已开始|开始了)\s*"
        r"(?:执行|处理|调研|搜索|检查|工作|跑|创建|添加)",
        r"(?:我会|我将|我来|我现在会|我现在将).{0,40}"
        r"(?:使用|调用|运行).{0,20}(?:工具|搜索|浏览器|web|x\s*搜索|终端|cron|定时任务)",
        r"(?:稍后|晚点|之后|完成后|查完后|调研完成后|跑完后).{0,60}"
        r"(?:给你|通知你|返回|汇报|发你|告诉你).{0,30}(?:结果|报告|结论|摘要)",
    )
)

_NEGATED_PROMISE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(?:i did not|i have not|i haven't|i cannot|i can't|i am not|i'm not)\b"
        r".{0,80}\b(?:start|started|working|running|executing|researching)\b",
        r"(?:我还没有|我没有|尚未|并未|不能|无法).{0,40}"
        r"(?:开始|执行|处理|调研|搜索|检查|工作|跑|创建|添加)",
    )
)


@dataclass(frozen=True)
class CommitmentGuardDecision:
    """Decision returned by :func:`evaluate_commitment_response`."""

    should_retry: bool
    should_block: bool
    reason: str = ""
    retry_prompt: str = ""
    fallback_response: str = ""
    tool_evidence_count: int = 0

    @property
    def violated(self) -> bool:
        return self.should_retry or self.should_block

    def to_metadata(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "tool_evidence_count": self.tool_evidence_count,
            "action": "retry" if self.should_retry else "block" if self.should_block else "allow",
        }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(value)


def response_claims_future_or_background_work(response: str) -> bool:
    """Return True when text promises work that should require evidence."""

    if not response or not response.strip():
        return False
    if any(pattern.search(response) for pattern in _NEGATED_PROMISE_PATTERNS):
        return False
    return any(pattern.search(response) for pattern in _COMMITMENT_PATTERNS)


def count_turn_execution_evidence(
    messages: Iterable[Mapping[str, Any]],
    *,
    current_turn_user_idx: int,
) -> int:
    """Count assistant tool calls or tool results after the current user turn."""

    count = 0
    for idx, msg in enumerate(messages):
        if idx <= current_turn_user_idx:
            continue
        if msg.get("role") == "tool":
            count += 1
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            count += len(tool_calls)
        elif tool_calls:
            count += 1
    return count


def _retry_prompt() -> str:
    return (
        "[System: Your last message claimed that you had started, would use "
        "tools, or would report results later, but this turn has no tool-call, "
        "job, log, or report evidence. Continue now by doing exactly one of "
        "these: (1) call the required tool(s) and then answer with concrete "
        "evidence, such as tool results, job id, log path, or report path; or "
        "(2) if you cannot execute the work, say plainly that you have not "
        "started and name the missing capability. Do not send another "
        "'I will get back to you' or 'I am working on it' message without "
        "execution evidence.]"
    )


def _fallback_response() -> str:
    return (
        "I did not actually start that work. Hermes blocked the previous "
        "response because it promised background/tool execution without any "
        "tool call, job id, log path, or report artifact in this turn."
    )


def evaluate_commitment_response(
    *,
    assistant_response: str,
    messages: Iterable[Mapping[str, Any]],
    current_turn_user_idx: int,
    enabled: bool = True,
    retry_count: int = 0,
    max_retries: int = 2,
    available_tool_names: Iterable[str] | None = None,
) -> CommitmentGuardDecision:
    """Evaluate whether a final text response needs tool execution evidence."""

    if not enabled:
        return CommitmentGuardDecision(False, False)

    has_tools = True
    if available_tool_names is not None:
        has_tools = any(True for _ in available_tool_names)
    if not has_tools:
        return CommitmentGuardDecision(False, False)

    evidence_count = count_turn_execution_evidence(
        messages,
        current_turn_user_idx=current_turn_user_idx,
    )
    if evidence_count > 0:
        return CommitmentGuardDecision(False, False, tool_evidence_count=evidence_count)

    if not response_claims_future_or_background_work(assistant_response):
        return CommitmentGuardDecision(False, False, tool_evidence_count=0)

    reason = "tool_free_execution_promise"
    if retry_count < max_retries:
        return CommitmentGuardDecision(
            should_retry=True,
            should_block=False,
            reason=reason,
            retry_prompt=_retry_prompt(),
            tool_evidence_count=0,
        )

    return CommitmentGuardDecision(
        should_retry=False,
        should_block=True,
        reason=reason,
        fallback_response=_fallback_response(),
        tool_evidence_count=0,
    )

from agent.commitment_guard import (
    count_turn_execution_evidence,
    evaluate_commitment_response,
    response_claims_future_or_background_work,
)


def test_detects_chinese_tool_free_research_commitment():
    response = "好的，我现在开始执行调研。我将使用工具进行信息收集，调研完成后直接给你结果。"

    assert response_claims_future_or_background_work(response)

    decision = evaluate_commitment_response(
        assistant_response=response,
        messages=[{"role": "user", "content": "现在开始调研吧"}],
        current_turn_user_idx=0,
        available_tool_names={"web_search"},
    )

    assert decision.should_retry is True
    assert decision.should_block is False
    assert decision.reason == "tool_free_execution_promise"
    assert "no tool-call" in decision.retry_prompt


def test_blocks_after_retry_budget_is_exhausted():
    decision = evaluate_commitment_response(
        assistant_response="I will use tools and report back with the result.",
        messages=[{"role": "user", "content": "Start the research."}],
        current_turn_user_idx=0,
        retry_count=2,
        max_retries=2,
        available_tool_names={"web_search"},
    )

    assert decision.should_retry is False
    assert decision.should_block is True
    assert "did not actually start" in decision.fallback_response


def test_allows_commitment_after_tool_evidence_exists():
    messages = [
        {"role": "user", "content": "Start the research."},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "call_1", "function": {"name": "web_search", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "search result"},
    ]

    assert count_turn_execution_evidence(messages, current_turn_user_idx=0) == 2

    decision = evaluate_commitment_response(
        assistant_response="I will report back after checking this.",
        messages=messages,
        current_turn_user_idx=0,
        available_tool_names={"web_search"},
    )

    assert decision.violated is False
    assert decision.tool_evidence_count == 2


def test_plain_answer_is_not_guarded():
    decision = evaluate_commitment_response(
        assistant_response="The logs show no tool calls in that turn.",
        messages=[{"role": "user", "content": "What happened?"}],
        current_turn_user_idx=0,
        available_tool_names={"web_search"},
    )

    assert decision.violated is False


def test_negated_commitment_is_not_guarded():
    assert not response_claims_future_or_background_work(
        "I did not actually start the work because no browser tool was available."
    )
    assert not response_claims_future_or_background_work(
        "我还没有开始调研，因为本轮没有任何工具调用。"
    )

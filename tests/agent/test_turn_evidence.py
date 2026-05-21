from agent.turn_evidence import collect_turn_evidence, format_turn_evidence_for_log


def test_collects_tool_calls_and_results_after_current_user_turn():
    messages = [
        {"role": "user", "content": "old"},
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "old_call", "function": {"name": "old_tool", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "old_call", "content": "old"},
        {"role": "user", "content": "search now"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "call_1", "function": {"name": "web_search", "arguments": "{}"}},
                {"id": "call_2", "function": {"name": "read_file", "arguments": "{}"}},
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "result"},
        {"role": "tool", "tool_call_id": "call_2", "name": "read_file", "content": "file"},
        {"role": "assistant", "content": "done"},
    ]

    evidence = collect_turn_evidence(messages, current_turn_user_idx=3)

    assert evidence["tool_call_count"] == 2
    assert evidence["tool_result_count"] == 2
    assert evidence["tool_names"] == ["web_search", "read_file"]
    assert evidence["tool_result_names"] == ["web_search", "read_file"]
    assert evidence["has_tool_evidence"] is True


def test_collects_commitment_guard_metadata():
    evidence = collect_turn_evidence(
        [{"role": "user", "content": "start"}],
        current_turn_user_idx=0,
        commitment_guard={"action": "block", "reason": "tool_free_execution_promise"},
    )

    assert evidence["commitment_guard"] == {
        "action": "block",
        "reason": "tool_free_execution_promise",
    }


def test_format_turn_evidence_for_log_is_compact():
    text = format_turn_evidence_for_log(
        {
            "tool_call_count": 2,
            "tool_result_count": 2,
            "tool_names": ["web_search", "read_file"],
            "commitment_guard": {
                "action": "retry",
                "reason": "tool_free_execution_promise",
            },
        }
    )

    assert text == (
        "tools=2 results=2 names=web_search,read_file "
        "guard=retry guard_reason=tool_free_execution_promise"
    )


def test_format_turn_evidence_handles_missing_data():
    assert format_turn_evidence_for_log(None) == "tools=0 results=0"

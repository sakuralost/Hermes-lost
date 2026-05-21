from gateway.run import _format_turn_evidence_for_gateway_log


def test_local_agent_result_preserves_turn_evidence_for_gateway_log():
    import inspect

    from gateway.run import GatewayRunner

    source = inspect.getsource(GatewayRunner._run_agent)

    assert (
        '"turn_evidence": result_holder[0].get("turn_evidence") '
        'if result_holder[0] else None'
    ) in source


def test_gateway_formats_turn_evidence_for_response_log():
    text = _format_turn_evidence_for_gateway_log(
        {
            "turn_evidence": {
                "tool_call_count": 1,
                "tool_result_count": 1,
                "tool_names": ["web_search"],
            }
        }
    )

    assert text == "tools=1 results=1 names=web_search"


def test_gateway_formats_missing_turn_evidence_without_crashing():
    assert _format_turn_evidence_for_gateway_log({}) == "tools=0 results=0"

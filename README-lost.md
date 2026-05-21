# Hermes-lost

Hermes-lost is a personal fork of `NousResearch/hermes-agent` focused on
making unattended agent work auditable instead of trust-based.

The first local change addresses a failure observed on the Hermes host: the
model replied that it had started a research task and would report results
later, but the session had no tool calls, no background job, no log path, and
no report artifact.

## Current Direction

- Keep Grok 4.3 in place for now and harden the runtime around it.
- Treat "I started", "I will use tools", and "I'll report later" as claims
  that require execution evidence.
- Force a retry when the model makes those claims without evidence.
- Block the response if the model still refuses to execute tools after the
  retry budget.
- Keep every change testable and easy to upstream or revert.

## First Patch

The commitment guard lives in `agent/commitment_guard.py` and is called from
the no-tool final-response path in `agent/conversation_loop.py`.

Default config:

```yaml
agent:
  commitment_guard:
    enabled: true
    max_retries: 2
```

## Validation

Run the focused tests:

```bash
python -m pytest tests/agent/test_commitment_guard.py
```

Run a broader agent smoke test before deploying this fork to the live host.

---
name: hermes-lost
description: Use when working on the Hermes-lost fork under /home/lost/lost/Hermes-lost, especially runtime guarantees for Hermes agent tool use, scheduled work, background-task evidence, gateway behavior, or Grok 4.3 control-plane reliability.
---

# Hermes-lost

Work in `/home/lost/lost/Hermes-lost`. This is a fork of
`NousResearch/hermes-agent` for hardening unattended agent execution.

## Priorities

- Prefer runtime validation over prompt-only rules.
- A response that says work has started, tools will be used, or results will
  arrive later must have evidence in the current turn: tool calls, tool
  results, a cron/job id, a log path, or a report path.
- When fixing failures, add focused tests near the touched subsystem.
- Keep changes small enough to deploy back to the live Hermes checkout after
  review.

## Useful Commands

```bash
cd /home/lost/lost/Hermes-lost
python -m pytest tests/agent/test_commitment_guard.py
git status -sb
```

## Live Instance Context

The live Hermes instance is installed at `/home/lost/.hermes/hermes-agent`.
Do not edit it directly while developing this fork unless the user explicitly
asks to deploy the tested patch.

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

## Version Discipline

- Treat `upstream/main` as the official Hermes reference.
- Treat `lost/test/<topic>` branches as experimental test versions.
- Treat `origin/main` as the user's stable Hermes-lost line.
- Do not bump package versions, create tags, merge branches, sync from upstream,
  deploy to live Hermes, or push to GitHub without explicit user approval for
  that operation.
- Before code changes, state the intended scope and wait for approval unless
  the user already asked for that exact change in the current turn.
- For each meaningful change, update `README-lost.md` with the upstream base,
  local commit or branch, modified files, validation result, deployment status,
  and upstream PR suitability.

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

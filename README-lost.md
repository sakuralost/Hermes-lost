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

## Version And Change Management

This fork must keep three lines of history distinct:

- **Official upstream**: `upstream/main`
  (`https://github.com/NousResearch/hermes-agent.git`). This is the reference
  for official Hermes behavior and potential upstream PRs. Do not edit this
  line directly.
- **Lost test version**: short-lived branches named `lost/test/<topic>`.
  Experimental fixes and new features start here. Each change needs a clear
  scope, expected behavior, validation command, and observed result.
- **Lost stable version**: `main` on `origin`
  (`https://github.com/sakuralost/Hermes-lost.git`). Only promote tested changes
  here after user approval.

Version numbers in `pyproject.toml`, release files, or tags must not be changed
casually. Prefer commit hashes, branch names, and this document's change log for
local tracking. Only change a package version or create a tag after asking the
user and receiving explicit approval.

Before any code change, merge, upstream sync, live deployment, version bump, or
GitHub push, the agent must ask the user for approval unless the user has
already requested that exact operation in the current turn. Documentation-only
updates requested by the user may be made directly, but still should not be
pushed without approval.

Every meaningful change should record:

- upstream base commit
- branch or commit used for testing
- modified files and behavior surface
- validation commands and results
- deployment status: not deployed, test deployed, or stable deployed
- upstream PR suitability: no, maybe, or yes

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

## Lost Change Log

### 2026-05-21 - Commitment Guard

- Base: `NousResearch/hermes-agent` commit `0c6eb96c8`.
- Local commit: `627fc0625 Add commitment guard for tool-free promises`.
- Scope: detect tool-free promises in the no-tool final-response path.
- Files: `agent/commitment_guard.py`, `agent/conversation_loop.py`,
  `agent/agent_init.py`, `hermes_cli/config.py`,
  `tests/agent/test_commitment_guard.py`.
- Validation:
  `python -m pytest tests/agent/test_commitment_guard.py tests/agent/test_tool_guardrails.py`
  passed with `18 passed`.
- Deployment status: not deployed to the live Hermes instance.
- Upstream PR suitability: maybe, after live testing and narrower review.

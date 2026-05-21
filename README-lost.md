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
- Deployment status: live deployed as part of the
  `lost/test/turn-evidence-audit` patch on 2026-05-21.
- Upstream PR suitability: maybe, after live testing and narrower review.

### 2026-05-21 - Turn Evidence Audit

- Base: `origin/main` commit `870ff6b1b`.
- Branch: `lost/test/turn-evidence-audit`.
- Scope: add structured per-turn evidence so logs can show whether a turn
  actually called tools or was blocked by the commitment guard.
- Files: `agent/turn_evidence.py`, `agent/conversation_loop.py`,
  `gateway/run.py`, `tests/agent/test_turn_evidence.py`,
  `tests/gateway/test_turn_evidence_log.py`.
- Validation:
  `python -m pytest tests/agent/test_turn_evidence.py tests/gateway/test_turn_evidence_log.py tests/agent/test_commitment_guard.py tests/agent/test_tool_guardrails.py`
  passed with `24 passed`.
- Deployment status: live deployed as part of the
  `lost/test/turn-evidence-audit` patch on 2026-05-21.
- Upstream PR suitability: maybe, after live testing and review for log format.

### 2026-05-21 - xAI Responses Transport Recovery

- Base: branch `lost/test/turn-evidence-audit` commit `6648fcf9e`.
- Branch: `lost/test/turn-evidence-audit`.
- Scope: recover from xAI/OpenAI Responses transport failures that were
  surfacing as generic `Connection error`, and make cron create failures more
  actionable when `schedule` is omitted.
- Files: `agent/codex_runtime.py`, `run_agent.py`, `tools/cronjob_tools.py`,
  `tests/run_agent/test_codex_xai_oauth_recovery.py`,
  `tests/tools/test_cronjob_tools.py`.
- Validation:
  `/home/lost/.hermes/hermes-agent/venv/bin/ruff check agent/codex_runtime.py run_agent.py tools/cronjob_tools.py tests/run_agent/test_codex_xai_oauth_recovery.py tests/tools/test_cronjob_tools.py`
  passed.
- Validation:
  `/home/lost/.hermes/hermes-agent/venv/bin/pytest tests/tools/test_cronjob_tools.py tests/run_agent/test_codex_xai_oauth_recovery.py`
  passed with `80 passed`.
- Validation:
  `/home/lost/.hermes/hermes-agent/venv/bin/pytest tests/agent/test_commitment_guard.py tests/agent/test_turn_evidence.py tests/gateway/test_turn_evidence_log.py tests/run_agent/test_streaming.py -k 'codex or commitment or evidence'`
  passed with `19 passed`.
- Live diagnosis: `/home/lost/.hermes/.env` had `HTTP_PROXY`,
  `HTTPS_PROXY`, and `ALL_PROXY` pointing at `127.0.0.1:7897`; in this host
  context that port refused connections. The config was backed up to
  `/home/lost/.hermes/.env.codex-backup-20260521-proxy` and changed to
  `proxy:7897`; a live `hermes -z '只回复：pong'` returned `pong`.
- Deployment status: live deployed to `/home/lost/.hermes/hermes-agent` as an
  uncommitted patch on top of upstream `0c6eb96c8`. Live validation passed:
  `hermes -z '只回复：pong'` returned `pong`; a commitment-guard probe refused
  to claim background work without evidence; a web-search research probe called
  `web_search`; a temporary cron smoke job ran successfully and saved output to
  `/home/lost/.hermes/cron/output/70d240838818/2026-05-21_12-26-17.md`.
- Runtime status: gateway is running manually in the live container as PID
  `355106`; Weixin is connected and the cron ticker is active.
- Upstream PR suitability: maybe. The Responses fallback is generally useful;
  the local proxy diagnosis is host-specific.

### 2026-05-21 - Gateway Evidence Propagation Fix

- Base: branch `lost/test/turn-evidence-audit` commit `c6e00b57e`.
- Branch: `lost/test/turn-evidence-audit`.
- Scope: preserve `turn_evidence` from the local agent result when the gateway
  builds the response payload, so Weixin/gateway logs report actual tool calls
  instead of `tools=0` after successful multi-tool turns.
- Files: `gateway/run.py`, `tests/gateway/test_turn_evidence_log.py`,
  `README-lost.md`.
- Validation:
  `/home/lost/.hermes/hermes-agent/venv/bin/ruff check gateway/run.py tests/gateway/test_turn_evidence_log.py`
  passed. `/home/lost/.hermes/hermes-agent/venv/bin/python -m pytest tests/gateway/test_turn_evidence_log.py tests/agent/test_turn_evidence.py`
  passed with `7 passed`.
- Deployment status: live deployed to `/home/lost/.hermes/hermes-agent` on
  2026-05-21. The gateway was restarted with `--replace` and is running as
  PID `368713`; `find_gateway_pids(all_profiles=True)` reported only
  `[368713]`.
- Upstream PR suitability: yes; this is a narrow observability correctness fix.

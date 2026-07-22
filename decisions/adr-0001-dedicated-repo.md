# ADR-0001: Governance lives in a dedicated repo, referenced globally

- **Status**: accepted
- **Date**: 2026-07-22
- **Deciders**: James

## Context

The framework must apply to every project (home monorepo, oracle suite, knox, future
commercial work) without being copied into each one. Candidate homes: inside
`home/.claude/`, a directory per project, or a standalone repo.

## Decision

We will keep the framework in a dedicated git repo at `~/Dev/claude-code/governance/`,
referenced globally via `~/.claude/CLAUDE.md`, installed skills, and hooks. Projects carry
only a thin `GOVERNANCE.md` manifest pinning standard versions.

## Alternatives considered

- **Inside `home/.claude/`** — couples framework history to an unrelated monorepo; global
  reach would still require symlinks.
- **Copy per project** — guaranteed drift; version pinning already gives projects stability
  without copies.

## Consequences

Single history and changelog for governance; skills/hooks need an install step
(`checks/install.sh`); projects must be able to resolve the repo path (hardcoded
`~/Dev/claude-code/governance`, acceptable for a single-user framework).

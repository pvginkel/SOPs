---
title: Re-run prompt-audit on the dev plugin
kind: periodic
project: AIWorkflow
when: >-
  After a model change: the model behind any dev-plugin role changes. Run it before reading the
  first slices run on the new model.
---

A new Opus or Sonnet release counts even with no edit at all: `MODELS` in `run_loop.py` /
`plan_loop.py` uses the `opus` / `sonnet` aliases. Four agents pin a model in frontmatter:
rebase-agent, test-agent and test-fixer on sonnet, refinement-writer on fable.

## Steps

1. [ ] In AIWorkflow, run `/claude-api prompt-audit` (the skill's `shared/prompt-audit.md`
   procedure) over `plugins/dev/agents`, `plugins/dev/skills`, `plugins/dev/docs` and the
   dispatch prompts in `run_loop.py` / `plan_loop.py`.
2. [ ] Re-read every finding at its file:line, and drop what doesn't hold.
3. [ ] Apply the survivors as one plugin version, with a `CHANGELOG-workflow.md` entry.
4. [ ] Add a row to the run log below.

## Why

Instructions drift relative to the newest model, and a frontier model executes old patches
literally (Anthropic's platform-cost post, 2026-09-08).

## Run log

| Date | Models | Findings | Applied in |
|---|---|---|---|
| 2026-09-09 | Opus 5, main roles | AIWorkflow `docs/research/platform-cost-read-2026-09-09.md` § 3.2 | 0.9.33 |

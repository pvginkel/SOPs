---
title: Install a pushed plugin version
kind: periodic
project: AIWorkflow
when: >-
  After pushing a version bump of the dev plugin (AIWorkflow) or the kubecoder plugin
  (KubeCoderConfig) by hand. The nightly card-pass does this itself for what it pushes.
---

The loops and every kc-spawned session run the installed copy,
`~/.claude/plugins/marketplaces/aiworkflow/`, a clone of GitHub, not the working tree in
`/work/AIWorkflow`. A push changes nothing until that copy is updated: it once sat on 0.9.8 for
nine days (2026-08-23 to 09-01) while 0.9.9 to 0.9.11 were pushed, and every run in between used
the old plugin.

`~/.claude` is the shared home, so one update reaches every environment. A running session keeps
the old copy until it restarts.

1. [ ] From any environment:

    ```
    claude plugin marketplace update aiworkflow
    claude plugin update dev@aiworkflow
    ```

    For KubeCoderConfig: `kubecoder-config` and `kubecoder@kubecoder-config`.

2. [ ] Installed version :: `~/.claude/plugins/installed_plugins.json` names the pushed version
3. [ ] Start a new session before planning or running a slice; the one you are in has the old copy.

## Background

AIWorkflow `CLAUDE.md` § Changing the plugin ("the installed copy is what actually runs");
Automation `card-pass` skill, its plugin-marketplace-repo rule.

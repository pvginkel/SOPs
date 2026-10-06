---
title: Re-capture the claude stand-in's goldens
kind: periodic
project: KubeCoder
when: >-
  After a Claude Code release: once the Claude Code binary in KubeCoder's local-home image has
  moved past the one the goldens record.
---

The goldens record the version they were captured from: `claudeVersion` in KubeCoder
`worker/internal/claudeshim/goldens/provenance.json` (2.1.261, captured 2026-09-11, when this
SOP moved here from Trello). Nothing detects the drift: the capture needs a logged-in credential,
so it can't be a CI gate, and upstream moves too often for a check to stay green.

## Steps

1. [ ] In a KubeCoder dev container, run the capture. Not the Go sidecar: it needs `claude`,
   tmux, python3 and a logged-in `~/.claude/.credentials.json`.

    ```
    worker/internal/claudeshim/goldens/capture.sh
    ```

2. [ ] `git diff` the goldens.
    - Only `provenance.json` changed: nothing drifted. Commit it, to record the version checked.
    - Anything else changed: the stand-in's fidelity has drifted. Read the delta, run the worker
      suite (the reader packages' agreement tests parse the goldens), then commit what the
      binary now emits.

!!! warning "If capture.sh stops"
    It writes nothing unless every file passes. On "still carries a live connector name", a
    connector is named inside a sentence, where the renamer can't tell where the name ends.
    Read the context it prints before deciding how to redact it.

## Background

Slice 210's refinement, and KubeCoder `worker/docs/claude-shim/goldens.md` § When a re-capture is
owed.

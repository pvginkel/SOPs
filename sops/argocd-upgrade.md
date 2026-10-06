---
title: Upgrade Argo CD
kind: periodic
project: Ansible
when: >-
  A new argo-cd Helm chart (argoproj/argo-helm) or Argo CD release. On 2026-10-06: chart 10.3.3,
  Argo CD v3.5.1 on argocd-prd.
---

The procedure is
[Upgrading Argo CD](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#upgrading-argo-cd)
in the Argo CD runbook. Argo syncs its own deploy repo by hand only, so nothing moves until you
sync.

1. [ ] Runbook steps 1 to 4 :: bump in ArgoCDDeploy, review the diff, sync, verify
2. [ ] Runbook step 5, the CLI :: DockerImages
   [`kube-coder-iac-toolchain/Dockerfile`](https://github.com/pvginkel/DockerImages/blob/main/kube-coder-iac-toolchain/Dockerfile)

!!! warning "Step 5 is the one that gets forgotten"
    The `argocd` CLI in every environment's `iac` sidecar is pinned to prd's server version. Until
    the image moves, every session reads the new server with the old CLI.

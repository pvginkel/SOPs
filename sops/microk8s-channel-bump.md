---
title: Bump the microk8s channel
kind: periodic
project: Ansible
when: >-
  A new microk8s minor on the stable channel. One minor per round: the playbook refuses a bigger
  step, so two minors behind is two rounds of this card, with a soak between.
---

The procedure is the Ansible runbook
[Rolling a microk8s cluster upgrade](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md).
Its every-bump duties sit in five sections; this card is their order.

`microk8s_channel` is pinned per cluster in `ansible/inventories/<inventory>/group_vars/k8s_<cluster>.yml`.
On 2026-10-06: prd `1.35/stable` (v1.35.6 live), dev `1.36/stable`, scratch `1.32/stable`.

!!! note "A bump on main rolls itself on Sunday"
    `IaC/Scheduled Update` runs `update-k8s.yml --limit k8s_prd` from `main` every Sunday around
    04:00, then `k8s_dev` if srvk8sdev is up. A bump pushed and not rolled by hand is rolled then,
    unattended.

## Before

1. [ ] Deprecated APIs :: [§ Before a channel bump](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#before-a-channel-bump-deprecated-apis-still-in-use).
   Query before the roll, on a cluster up long enough for Argo CD to have reconciled every app.
   A series with `removed_release` at or below the target minor blocks the bump; an empty
   `removed_release` is not a pass forever. Covers prd only.
2. [ ] Where CoreDNS sits :: [§ Drain that succeeds and takes a service down anyway](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#drain-that-succeeds-and-takes-a-service-down-anyway).
   One replica, no PDB: every roll is a short cluster-DNS gap unless you scale it to 2 for the run.
3. [ ] Workstation DNS :: a resolver not hosted on the cluster being rolled
   ([§ Workstation DNS during a roll](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#workstation-dns-during-a-roll)).
4. [ ] Bump `microk8s_channel` by one minor in the cluster's `group_vars`, commit.

## Roll

Per [§ Run](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#run),
from `ansible/`, one cluster at a time:

1. [ ] scratch, if the playbook itself changed :: `--limit k8s_scratch` (two nodes, exercises drain/uncordon)
2. [ ] srvk8sdev :: `--limit srvk8sdev` (single node, drain skips; it is off by default, start it first)
3. [ ] prd :: `--limit k8s_prd`, a few minutes per node, four nodes
4. [ ] Verify :: [§ Verify](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#verify):
   every node `Ready`, same kernel. That section's one-time pre-drain hand-off check is still owed
   on the next multi-node prd roll: watch the task against `keycloak`.

A node whose refresh goes sideways: `snap revert microk8s`
([§ Rollback](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#rollback)).

## After a soak of a few days

1. [ ] Refresh the addons, in a maintenance window ::
   [§ Refreshing addons](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#refreshing-addons-after-a-microk8s-upgrade).
   Not bundled with the roll, so an addon regression is told apart from a microk8s one.

!!! warning "The dns addon window"
    `refresh-k8s-addons.yml` disables and re-enables each addon. For `dns` that deletes CoreDNS:
    nothing in the cluster resolves until it is back, and anything that reconnects by hostname can
    take collateral restarts. The re-enable resets CoreDNS to one replica; the play restores the
    MetalLB pool itself.

## Re-evaluate the two workarounds

Each bump, before closing the round:

1. [ ] dqlite watch-freeze watchdog :: does the new channel's `k8s-dqlite` carry
   [PR #365](https://github.com/canonical/k8s-dqlite/pull/365)? The runbook's last word: unmerged,
   in no release (1.35 and 1.36 included). Once it ships, remove the per-node
   `dqlite-watchdog.timer` per
   [§ Re-evaluate the dqlite watch-freeze watchdog](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#re-evaluate-the-dqlite-watch-freeze-watchdog)
   and [dqlite-watch-freeze.md](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/dqlite-watch-freeze.md),
   or keep it as a deliberate net.
2. [ ] Calico CNI-token refresh job :: `IaC/Scheduled Calico Rollout` works around
   [calico#8777](https://github.com/projectcalico/calico/issues/8777). Read the bundled Calico
   version (the command is in
   [§ Re-evaluate the Calico CNI-token refresh job](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#re-evaluate-the-calico-cni-token-refresh-job))
   against the issue; retire the job when the fix ships, or keep it as a net.

## Background

Ansible `CLAUDE.md` § Cluster upgrades carries the watchdog duty as an instruction to sessions.

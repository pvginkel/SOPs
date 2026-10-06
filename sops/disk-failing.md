---
title: A disk is failing
kind: abnormal
project: Ansible
when: >-
  A disk throws errors or dies: a Ceph OSD SSD, the NVMe behind zpool2, a PVE host's own NVMe,
  or the local-backup HDD.
---

Nothing watches disk health. There is no SMART monitoring on the PVE hosts and no Ceph or ZFS
alert in Prometheus (2026-10-06): you learn of a failure from Ceph's health, a pool's state, a
host error or a workload falling over. Only the Ceph OSD swap has a written procedure. This card
says what each disk carries, so you know what is at stake, and where the one procedure is.

Which disk is which, with serials: [homelab-handover §2](https://github.com/pvginkel/Ansible/blob/main/docs/homelab-handover.md#2-storage).
The passthrough paths are the `passthrough_disks` entries in
[`terraform/prd/vms.tf`](https://github.com/pvginkel/Ansible/blob/main/terraform/prd/vms.tf).

## Identify

| Disk | What it carries | What survives | Procedure |
|---|---|---|---|
| A Ceph OSD SSD: Samsung 870 EVO 2 TB, one per host, passed through to srvceph1/2/3 | One of three replicas of everything on Ceph | Ceph is 3× replicated, one copy per host: degraded, not down | [vm-rebuild § Disk passthrough](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/vm-rebuild.md#disk-passthrough--replacing-a-failing-osd-disk), the PVE and Terraform side. The Ceph side (OSD out, re-add on the new disk, rebalance) has none written: prd Ceph is not Ansible-managed |
| The NVMe behind `zpool2`: Samsung 980 500 GB on `pve`, passed through to srvk8s1 | The storage chart and its Samba share, mydownloads, Prometheus's data | Nothing: one disk, no redundancy. Their pods are pinned to `homelab.local/storage=zpool2` and stay Pending until a pool is back | None written. [k8s-rebuild § Primary rebuild](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md#primary-rebuild--srvk8s1-nvme-passthrough) re-attaches an intact NVMe to a new srvk8s1; a new disk also means a new by-id path in `vms.tf` and an empty pool |
| A PVE host's NVMe: `local` and `local-lvm` | Every managed VM disk on that host, zpool3/4/5 included | No HA, no replication, nowhere to migrate to. Guests on pve1 and pve2 have no vzdump at all; `pve`'s backed-up guests have at most three nightly dumps on `local-backup` | None written for the host. Per VM, the rebuild runbooks: [k8s-rebuild](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md), [openbao § Single-node loss](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#2--single-node-loss), [iac-agent § Rebuild srviac](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#rebuild-srviac-from-scratch). A Ceph node has an outline only: [vm-rebuild § k8s and Ceph cluster members](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/vm-rebuild.md#rebuild-flow--k8s-and-ceph-cluster-members) |
| `local-backup`: Seagate ST2000LM015 2 TB HDD on `pve` | The vzdump artifacts (daily 04:00, keep-last 3) | Every service. Losing it loses backups, not workloads | None written |

## Read-only checks

1. [ ] Ceph :: `ssh root@pve1 "qm guest exec 113 --timeout 60 -- microceph.ceph -s"`, then `ceph osd df` the same way (the prd Ceph nodes reject the ansible key; srvceph1 is VM 113)
2. [ ] zpool2 :: `zpool status` on srvk8s1, expect `ONLINE`
3. [ ] A PVE host :: `qm list` for what is running, and what the vzdump job last wrote on `local-backup`

!!! warning "Before touching Ceph"
    `ceph osd set noout` before a Ceph node or OSD goes down on purpose, and `unset` after, as
    in [Shutting down a PVE host](pve-host-shutdown.md). The OSD swap in vm-rebuild hot-swaps the
    disk with the VM running.

## Background

The capacity picture and why a node has nowhere to fail over to:
[homelab-handover §6](https://github.com/pvginkel/Ansible/blob/main/docs/homelab-handover.md#6-failure-characteristics--read-this-before-planning-capacity).

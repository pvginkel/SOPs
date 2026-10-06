---
title: Terraform change that needs a node reboot
kind: normal
project: Ansible
when: >-
  A terraform/prd change to a cluster member's memory, CPU, NICs, disks, BIOS or machine type:
  anything PVE applies only at the next power cycle.
---

Terraform never reboots a managed VM. The `managed-vm` module sets `reboot_after_update = false`,
so an apply writes the change to PVE as a `[PENDING]` section in
`/etc/pve/qemu-server/<vmid>.conf` on the VM's host, where it waits for a power cycle. The drain
and the cycle are Ansible's, one node at a time (AnsibleSpecs `decisions.md`, "Terraform applies
on cluster members never reboot directly").

!!! danger "Two things not to do"
    Never apply and then reboot by hand on a live cluster member. And never use a guest-side
    `reboot` for this: it does not power-cycle QEMU, so `[PENDING]` stays unmerged. Only
    `qm shutdown` then `qm start` on the PVE host merges it.

## k8s node (srvk8s1–4, srvk8sdev)

1. [ ] Push, then apply :: `IaC/Apply`, or `cd terraform/prd && cexec iac terraform apply`. The
   node keeps running its old shape.
2. [ ] It landed as pending :: a `[PENDING]` section in `/etc/pve/qemu-server/<vmid>.conf` on its
   PVE host
3. [ ] srvk8s4 :: it hosts every KubeCoder environment, so commit and save your work first
   ([pve-host-shutdown.md](pve-host-shutdown.md))
4. [ ] Apply it :: `cd ansible && poetry run ansible-playbook playbooks/update-k8s.yml --limit <node>`.
   It sees the pending section, hands off and drains the node, cold-cycles it from its PVE host,
   waits for it to rejoin, uncordons. Anything else pending (apt, snap) rides along; that is by
   design. Several nodes: `--limit k8s_prd` rolls them one at a time.
5. [ ] Verify :: every node `Ready`, none cordoned; the `[PENDING]` section gone

Drain stuck:
[k8s-upgrade.md § Drain blocked by a PodDisruptionBudget](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#drain-blocked-by-a-poddisruptionbudget).

## Ceph node (srvceph1–3)

!!! warning "No playbook"
    The prd Ceph fleet is not Ansible-managed yet: `site-ceph.yml` reaches `ceph_dev` only, and
    `update-ceph.yml` is future work. This is the k8s flow by hand. Not yet exercised as such.

1. [ ] On a Ceph node :: `ceph osd set noout`
2. [ ] Apply Terraform, as above
3. [ ] On its PVE host :: `qm shutdown <vmid>`, and once it is stopped, `qm start <vmid>`
   (srvceph1 is 113 on pve1, srvceph2 114 on pve2, srvceph3 115 on pve)
4. [ ] Ceph :: `ceph osd unset noout`, then `HEALTH_OK`
5. [ ] The next node only after `HEALTH_OK`

!!! note "srvvault1–3 and srviac"
    Same `reboot_after_update = false`, and their `unattended-upgrades` reboot is a guest reboot,
    so it never merges a pending change either. No drain to do: `qm shutdown` then `qm start` by
    hand, one srvvault at a time, since the Raft quorum survives one node rebooting, not two.
    srviac is the Jenkins agent, so cycle it from the pod or wrkdev, not from a job.

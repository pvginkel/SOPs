---
title: After a hardware change
kind: normal
project: Ansible
when: >-
  A disk, RAM module, NIC or whole host was added, replaced or removed on pve, pve1 or pve2, or
  the network edge changed.
---

The physical layer has one written record: Ansible
[`docs/homelab-handover.md`](https://github.com/pvginkel/Ansible/blob/main/docs/homelab-handover.md).
Its hardware facts were read from the live machines on 2026-08-09 and nothing regenerates them:
no inventory, role or Terraform resource records a CPU, RAM or physical-disk fact for a PVE node,
and `host_vars/pve1.yml` and `pve2.yml` do not exist. The logical layer (VM shapes, MACs,
affinity, networks) is repo-derived and stays true by itself.

The doc does not say which commands it was read with. Read each fact from the node itself: the
PVE web UI (`https://<node>.home:8006`, Shell) or `ssh root@<node>` with the `id_ed25519_pve`
key (handover §5).

## Before the change

1. [ ] Powering a host off :: [pve-host-shutdown.md](pve-host-shutdown.md)
2. [ ] Replacing a Ceph OSD disk ::
   [vm-rebuild.md § Disk passthrough](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/vm-rebuild.md#disk-passthrough--replacing-a-failing-osd-disk):
   hot-swap with `qm set`, the new `/dev/disk/by-id/` path into `terraform/prd/vms.tf`, then
   `terraform refresh`. The Ceph side, re-adding the OSD, is by hand.

## After: re-verify the handover

1. [ ] §1 Physical nodes :: CPU, RAM, PVE version and kernel, per node and the cluster totals
2. [ ] §2 Storage :: which NVMe, SSD and HDD sit in which node; the OSD disk serials
   (`ls /dev/disk/by-id/`); the datastores. The spare `/dev/sda` on pve is recorded as
   `intentional_spare_disks` in `ansible/inventories/prd/host_vars/pve.yml`: update it if the
   spare was used or pulled.
3. [ ] §3 Network :: NIC names behind `vmbr0` and `vmbr1`, and the USB 2.5 GbE adapters on
   pve1/pve2. Bridges are hand-configured (`/etc/network/interfaces`, no role), so this is their
   only description. The UDM section if the edge changed.
4. [ ] §6 Failure characteristics :: the RAM-committed table and "Current headroom warnings". A
   RAM change moves the "nowhere to fail over to" arithmetic; VM allocations are `memory_mb` in
   `terraform/prd/vms.tf`.
5. [ ] §4 only if a VM moved host :: `pve_node` in `vms.tf` is the source. The architecture
   model (`docs/architecture/ansible-architecture.yaml`) names the VMs each host carries in its
   node summaries.
6. [ ] Update the provenance date in the doc, commit

## A new or rebuilt host

!!! warning "No runbook installs a PVE node"
    Nothing covers a bare-metal PVE install or cluster join. Bridges (`vmbr0` untagged plus VLAN
    2, `vmbr1` on the backplane) are out of band and set by hand; handover §3 has the addresses
    and the NIC assignment.

1. [ ] Adopt it ::
   [adoption.md](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/adoption.md):
   `adopt.yml` with `adoption_user=root` and `adoption_known_hosts_file=proxmox`, wire the file
   into `ansible.cfg`, `site.yml --check`, then the one-time `passwd pvginkel`
2. [ ] Inventory :: the `proxmox` group in `ansible/inventories/prd/hosts.yml`;
   `host_vars/<node>.yml` only if it holds the vzdump datastore (`pve_node_backup_datastore`)
   or a spare disk
3. [ ] Terraform :: `pve_node` on the VMs it carries in `vms.tf`. CPU affinity is zoned on `pve`
   only.
4. [ ] The architecture model's node list, then the handover sections above

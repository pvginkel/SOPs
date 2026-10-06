---
title: Bringing srvk8sdev up
kind: normal
project: Ansible
when: Before starting srvk8sdev (VM 919 on pve), and before turning it off again.
---

srvk8sdev is the single-node dev cluster: microk8s (`k8s_dev`) with a co-located microceph
(`ceph_dev`). It is off by default, `on_boot = false` in Ansible
[`terraform/prd/vms.tf`](https://github.com/pvginkel/Ansible/blob/main/terraform/prd/vms.tf)
since 2026-10-03, and Terraform ignores whether it runs. Nothing depends on it and nothing starts
it but you. Every weekly job skips a dev host it cannot reach: `IaC/Scheduled Certs` (Friday) and
`IaC/Scheduled Update` (Sunday) go UNSTABLE on their dev stage, and `IaC/Apply` converges it last
in a stage that can only go UNSTABLE. So each time it comes up it owes what it missed.

Ansible commands run from the checkout's `ansible/`; in a KubeCoder environment put `cexec iac`
after the `cd`.

## Before

1. [ ] What waits for it :: YouTrack `#Unresolved srvk8sdev` and `#Unresolved "dev cluster"`
2. [ ] Start it :: `ssh root@pve qm start 919`
3. [ ] Reachable :: `cd ansible && poetry run ansible k8s_dev -m ping`

## Catch up

Every time, in this order: SSH first, because every playbook rides on it.

1. [ ] SSH host certificate. The ping decides:
    - `pong`: `cd ansible && poetry run ansible-playbook playbooks/renew-host-certs.yml --limit k8s_dev`
      (a no-op outside the 14-day window).
    - `UNREACHABLE` with `Certificate invalid: expired`: it lapsed while off.
      [Re-issue it](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/ssh-host-cert-expiry.md#vms-terraform-builds-from-scratch)
      with `playbooks/reissue-host-cert.yml -e reissue_target=srvk8sdev`. srvk8sdev is built
      from scratch, so the playbook pins its key from `terraform output`.
2. [ ] TLS leaf for `kubernetes-api-dev.home` ::
   `cd ansible && poetry run ansible-playbook playbooks/renew-internal-tls.yml --limit k8s_dev`
   — a lapsed leaf needs nothing more
   ([internal-tls-expiry.md § Notes](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/internal-tls-expiry.md#notes))
3. [ ] OS and microk8s ::
   `cd ansible && poetry run ansible-playbook playbooks/update-k8s.yml --limit srvk8sdev`
   ([k8s-upgrade.md § srvk8sdev](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#srvk8sdev-single-node-smoke)).
   Single node, so no drain: the dev cluster is down while it reboots.
4. [ ] If `IaC/Apply` ran while it was off, its dev stage was skipped. By hand:
   `cd ansible && poetry run ansible-playbook playbooks/site-k8s.yml --limit k8s_dev --skip-tags os_update`,
   then `playbooks/site-ceph.yml --skip-tags os_update`.

!!! note "Left up over a weekend"
    The Friday and Sunday jobs run their dev stages themselves once srvk8sdev answers. The
    catch-up above is for the day you start it.

## Then

Do what you came for. Runbooks that need it:
[s3-mirror.md § Restore drill](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/s3-mirror.md#5--restore-drill),
[k8s-rebuild.md § srvk8sdev](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md#rebuild--srvk8sdev-single-node-dev).
From a KubeCoder environment it answers on SSH, 16443 and RGW's port 80, and the default
kubeconfig reads it with `kubectl --context dev`
([live-infra-access.md](https://github.com/pvginkel/Ansible/blob/main/docs/live-infra-access.md)).

## After

1. [ ] Shut it down :: `ssh root@pve qm shutdown 919`
2. [ ] Leave `on_boot = false` alone. Next Sunday's `IaC/Scheduled Update` goes UNSTABLE on its
   dev stage again: expected, leave it.

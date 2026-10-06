---
title: Estate down, or a power cut
kind: emergency
project: Ansible
when: >-
  All three PVE hosts restarted together, or everything is unreachable at once. The first sign
  is often healthchecks.io on Telegram: Prometheus's heartbeat stopped.
order: 10
---

The procedure is the Ansible cold-boot runbook, mirrored on this site: the order the layers come
back in, a check per layer, and a break-glass move for each layer that doesn't. This card is the
desk: where you work from while the usual tools are down, and which runbook each symptom leads to.

## Before you start

1. [ ] KubeCoder is down :: every environment runs on srvk8s4, which takes its address from the
   in-cluster DHCP, so it is off the LAN until DHCP is back. Don't wait for it.
2. [ ] Work from wrkdev :: VM 112 on `pve`, static `10.1.0.18`, `onboot: 1`, so it is back a
   minute after `pve` is. Or the desktop with a static address: the `netsh` recipe is under
   [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass),
   "The operator desktop without DHCP". Mask `255.255.0.0`, not `255.0.0.0`.
3. [ ] Names are down with DNS :: reach hosts by IP. The address list is at the end of
   [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass).
4. [ ] kubectl :: `ssh ansible@srvk8s1 sudo microk8s kubectl …` (srvk8s1 is `10.1.0.27`) until
   srvk8s4 is back. SSH by IP needs the host certificate's name: the recipe is under Break-glass,
   "SSH by IP".
5. [ ] Keys :: `~/.ssh/id_ed25519_ansible` for the VMs, `id_ed25519_pve` for `root` on the PVE
   hosts. If the workstation is gone too, the ansible key is in RoboForm under "Homelab SSH key".
6. [ ] An Ansible checkout :: `ansible/files/known_hosts.d/homelab` is the SSH CA the recipe
   checks against.
7. [ ] SSO is down until Keycloak is back :: the Argo CD and Jenkins local `admin` passwords are
   in RoboForm ("Admin logins without Keycloak", under Break-glass).
8. [ ] The UDM :: not estate-managed; its credentials are in RoboForm.

## Identify

| You see | Go to |
|---|---|
| The three PVE hosts rebooted together and things are coming back | [What happens on its own](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#what-happens-on-its-own), then watch [Order and checks](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#order-and-checks) top to bottom and step in at the first layer that doesn't come up |
| A layer stays down: the `dhcp` pod not Ready, a pinned image `NotFound`, no SSO, a hook Job clash | [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass) |
| New pods aren't created: `FailedCreate` events name `mpol.validate.kyverno.svc-fail` | [Kyverno refuses new pods](kyverno-break-glass.md) |
| Kubernetes is up, but no DHCP or DNS in the house | [No DHCP or DNS in the house](no-dhcp-dns.md) |
| Kubernetes is up, but every `.home` and `webathome.org` host is unreachable | [Front-door nginx down](front-door-nginx-down.md) |
| OpenBao stays sealed or a node is gone; srviac's `iac` won't start | [OpenBao is down](openbao-recovery.md), [IaC agent cold boot](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-cold-boot.md) |
| The cluster is back on its nodes but empty: no namespaces, no objects | [Workloads on a rebuilt cluster](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cluster-bootstrap.md) |
| One k8s node is gone or won't rejoin | [Rebuilding k8s VMs](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md) |
| After a rebuild, every KubeCoder environment's `kubectl` is refused | [KubeCoder lost cluster access](kubecoder-cluster-access-lost.md) |

!!! danger "New hardware: fire, theft, nothing left"
    There is no master site-recovery runbook yet. OpenBao is not first: its listener certificate
    comes from step-ca, which runs on Kubernetes. The order is bare metal, core VMs, the k8s
    control plane and Ceph, [step-ca](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-bootstrap.md),
    then OpenBao ([Whole-cluster loss](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#3--whole-cluster-loss)),
    then ESO and the workloads that need OpenBao.

## Then

Work the runbook top to bottom. Every VM has `onboot` and no startup order, so the layers come
back on their own through retries; the job is to watch and to step in at the first layer that
doesn't. On 2026-09-25 everything recovered unaided except Keycloak, whose pinned image digest
had been garbage-collected from the registry and which held the `dhcp` pod not Ready for 2h45m,
and srvk8s4, NotReady until DHCP answered. Done at step 8 of Order and checks: every Argo
Application Synced and Healthy.

Afterwards, undo what you did by hand: the desktop's static address, and the `dhcp` Service
patch once the pod is Ready.

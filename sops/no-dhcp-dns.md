---
title: No DHCP or DNS in the house
kind: emergency
project: Ansible
when: >-
  Telegram shows DHCPNotAnswering or LoadBalancerNotAnnounced for dnsmasq-prd; devices can't
  get a lease; .home names don't resolve; or healthchecks.io says Prometheus's heartbeat stopped.
order: 20
---

DHCP and DNS for the whole house run inside the Kubernetes cluster (DnsmasqDeploy, namespace
`dnsmasq-prd`): DNS is `dns-0`/`dns-1` on `10.2.1.2`/`10.2.1.3`, DHCP is the `dhcp` pod on
`10.2.1.10`. The UDM relays every LAN's DHCP to `10.2.1.10` and serves none of its own: there is
no fallback on the router.

!!! warning "The clock is the lease"
    Leases last 1 day and renew at 12 h, so devices drop off over the following hours, not at
    once, and the last ones a day after the address went dark. `DHCPNotAnswering` fires 12
    minutes after the last OFFER; with the whole cluster down nothing fires at all, and the only
    signal is healthchecks.io.

## Identify

| You see | Go to |
|---|---|
| Nothing answers: no VIPs, no `.home`, heartbeat stopped | The cluster is down: [Estate down](estate-cold-boot.md) |
| `DHCPNotAnswering`, `LoadBalancerNotAnnounced` for `dnsmasq-prd/dhcp`; `.home` still resolves | The `dhcp` pod is not Ready, so MetalLB withdrew `10.2.1.10`. First move: publish the not-ready endpoint, the one-line patch at the top of [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass). DHCP is back seconds later. Then fix the pod |
| `.home` names don't resolve; leases are fine | `dns-0`/`dns-1`: the checks are step 6 of [Order and checks](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#order-and-checks). No deeper procedure is written |
| srvk8s4 NotReady and KubeCoder gone | Expected: it has a DHCP address (`10.1.3.5`) and rejoins once DHCP answers ([What happens on its own](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#what-happens-on-its-own)) |

## Before you start

1. [ ] Your own machine may have no address :: nothing is wrong with it. wrkdev is static
   (`10.1.0.18`) and works. The desktop needs a static address: the `netsh` recipe is under
   [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass),
   "The operator desktop without DHCP".
2. [ ] KubeCoder is down with srvk8s4 :: kubectl is `ssh ansible@srvk8s1 sudo microk8s kubectl …`.
   If DNS is down too, by IP (`10.1.0.27`) with the "SSH by IP" recipe under Break-glass.
3. [ ] Keys :: `~/.ssh/id_ed25519_ansible`; RoboForm "Homelab SSH key" if the workstation is gone.

## Then

Step 6 of [Order and checks](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#order-and-checks)
is the check per symptom: pods Ready, every EndpointSlice endpoint `ready: true`, MetalLB
announcing all three addresses, `dig` answering, DHCPACKs in the log. A missing MetalLB status
means a not-ready endpoint: the address is dark on the LAN even though the pod exists.

On 2026-09-25 the pod stayed not Ready for 2h45m because its DHCPApp sidecar crash-looped on
Keycloak's OIDC discovery. DHCPApp is out of the `dhcp` pod since, so that chain is gone; the
patch still covers whatever holds the pod not Ready next time.

!!! note "Undo the patch"
    The chart pins `publishNotReadyAddresses` to `false`, so Argo shows the patch as drift and
    the next DnsmasqDeploy sync reverts it. Don't push DnsmasqDeploy while DHCP depends on the
    patch; once the pod is Ready, sync or patch it back.

Background: Ansible [`homelab-handover.md` §6](https://github.com/pvginkel/Ansible/blob/main/docs/homelab-handover.md#6-failure-characteristics--read-this-before-planning-capacity),
the alert rules in PrometheusDeploy `config/prd/values.yaml` (groups `dhcp` and
`loadbalancers`), and the incident in AnsibleSpecs `handovers/dhcp-outage-2026-09-25/`.

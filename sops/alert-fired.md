---
title: A Telegram alert fired
kind: abnormal
project: Ansible
when: >-
  An Alertmanager alert, a red or unstable scheduled IaC job, or a healthchecks.io message
  reaches Telegram.
---

Three senders share the channel. Which one it is tells you where to look.

| The message | Comes from | Go to |
|---|---|---|
| `[FIRING] <AlertName>`, then `host:`, a summary and a description | Prometheus's rules through Alertmanager. Critical alerts ring; warnings arrive silent | [Alerts](#alerts) below |
| A job name, a build link and the build description | jenkins-telegram-bot, on a FAILURE of any build. UNSTABLE and ABORTED are raised by the job itself | [Scheduled jobs](#scheduled-jobs) below |
| healthchecks.io: the Prometheus heartbeat stopped | Alertmanager's pings stopped: Prometheus, Alertmanager or the whole cluster is down | [Heartbeat](#heartbeat) below |

The rules, with every threshold and its reasoning, are PrometheusDeploy
[`config/prd/values.yaml`](https://github.com/pvginkel/PrometheusDeploy/blob/main/config/prd/values.yaml)
under `serverFiles.alerting_rules.yml`. Firing alerts are at `https://prometheus.home`, silences
at `https://alertmanager.home`. The `kubectl` lines below need a prd kubeconfig; from a KubeCoder
environment `cexec iac kubectl --context prd …` reads, and `--kubeconfig ~/.kube/config-prd-write`
writes.

## Alerts

The description in the message says what to check first. Where a runbook exists it is linked;
"none written" means the description is all there is.

| Alert | Procedure |
|---|---|
| `BackupOverdue` | [backup-freshness §1](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/backup-freshness.md#1--backupoverdue-fires). If `BackupWatcherBlind` fires too, start at §2 |
| `BackupWatcherBlind` | [backup-freshness §2](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/backup-freshness.md#2--backupwatcherblind-fires) |
| `S3MirrorStale` | [s3-mirror § What can go wrong](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/s3-mirror.md#what-can-go-wrong) |
| `ArgoCDSyncStillFailed`, `ArgoCDHealthStillDegraded`, and Argo's own `ArgoCDSyncFailed` / `ArgoCDHealthDegraded` (events; they never send a "resolved") | [argocd § Diagnosing a failed sync](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#diagnosing-a-failed-sync); the app at `https://argocd.home/applications/<name>` |
| `ArgoCDAlertsBlind` | None written. The controller pod in `argocd-prd` is down, or its metrics Service lost its scrape annotation: [argocd § Reading Argo without the CLI](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#reading-argo-without-the-cli) |
| `DHCPNotAnswering`; `LoadBalancerNotAnnounced` for `dnsmasq-prd/dhcp` | [No DHCP or DNS in the house](no-dhcp-dns.md) |
| `LoadBalancerNotAnnounced` for any other Service | None written. MetalLB withdraws a Service with no ready endpoints: the description's `kubectl` lines find the pod |
| `MetalLBAnnouncementsBlind` | None written. No speaker in `metallb-system` scraped for 10 m |
| `DHCPProbeStale` | None written. srviac is down, or its `dhcp-probe.timer` stopped: [iac-agent § srviac is unreachable](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#srviac-is-unreachable) |
| `OIDCDiscoveryFailing` | Keycloak. Every SSO login fails and OIDC apps crash-loop by design: [cold-boot § Order and checks](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#order-and-checks) step 7, and [§ Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass) for the local admin logins |
| `OIDCDiscoveryUnprobed` | None written. The `blackbox-exporter` pod in `prometheus-prd` |
| `PodStuckInBackOff` | None written. `ImagePullBackOff` with `NotFound` on a pinned digest: [cold-boot § Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass) |
| `NodeNotReady` | None written. A VM that is gone: [k8s-rebuild](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md) |
| `NodeMemoryStalled`, `NodeMemoryStallElevated` | None written. Detection only: kubelet cannot evict on PSI. Compare the node's memory requests with its usage and look for requestless workloads |
| `NodeMemoryStallCounterWedged` | None written. The kernel's PSI counter is stuck, not the node; the node's stall alerts are blind until it is rebooted, which resets the counter |
| `NodeKubeReservedMissing` | A snap refresh rewrote `args/kubelet`. `site-k8s.yml` re-asserts it: run `IaC/Apply` ([iac-agent § Routine](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#routine-push-to-main-then-apply)) |
| `Heartbeat` | Never reaches Telegram. Always firing, by design |

## Scheduled jobs

Every `iac-*` job ends `UNSTABLE` with `srvk8sdev is unreachable — … skipped` while srvk8sdev is
off, which is its default. That is expected, and for `IaC/Scheduled Update` the operator accepted
the weekly yellow build as is (2026-10-04). Any other `UNSTABLE` stage is real: read it. An
`aborted (timeout or hand)` message means the job was cut off; an apply cut off is left half
converged, so run `IaC/Apply` again.

| Job | A red build |
|---|---|
| `IaC/Scheduled Drift` (daily, 11:xx) | Read-only. The build description names the drift under its stage. Ansible tasks `changed` under `--check`, or a Terraform plan with changes: a push nobody applied, so run `IaC/Apply` ([iac-agent § Routine](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#routine-push-to-main-then-apply)), or a host changed by hand. A VM Terraform refuses to destroy, or a tainted one: [vm-rebuild § If a rebuild goes sideways](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/vm-rebuild.md#if-a-rebuild-goes-sideways). An `internal_tls` leaf under 7 days: the Certs job missed its Friday, [internal-tls-expiry](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/internal-tls-expiry.md). `https://ca.home/roots.pem differs`: the CA was rotated without the repo, or the repo's `homelab-root.crt` edited without the CA; no procedure beyond [step-ca-root-rotation § The trust anchor](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-root-rotation.md#the-trust-anchor-and-every-copy-of-it) |
| `IaC/Scheduled Certs` (Fridays) | The description says which stage: `host certs may lapse` is [ssh-host-cert-expiry](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/ssh-host-cert-expiry.md), `internal_tls leaves may lapse` is [internal-tls-expiry](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/internal-tls-expiry.md); its § Cause reads both. Two red Fridays in a row and a certificate lapses |
| `IaC/Scheduled Update` (Sundays) | The prd OS roll failed mid-drain or mid-reboot. A drain blocked by a PDB: [k8s-upgrade § Drain blocked by a PodDisruptionBudget](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#drain-blocked-by-a-poddisruptionbudget), whose recovery re-runs `update-k8s.yml` on the remaining nodes |
| `IaC/Scheduled Calico Rollout` (Wednesdays) | The prd `calico-node` restart failed. What the job prevents, and the playbook to run by hand: [k8s-upgrade § Re-evaluate the Calico CNI-token refresh job](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-upgrade.md#re-evaluate-the-calico-cni-token-refresh-job) |
| `IaC/Scheduled Secret Rotation` (nightly 05:30) | Red only when the run itself broke; a failed rotation is posted to Telegram by the rotator and stays green. [openbao §5 Rotation](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#5--rotation). Disabling the job is the immediate stop |

!!! note "Secret Rotation is not on the controller yet"
    As of 2026-10-06 the job does not exist: SecretRotator's go-live creates it.

## Heartbeat

The `Heartbeat` rule pings a healthchecks.io check through Alertmanager at most 2 minutes apart;
the check's period is 5 minutes, and its Telegram integration lives in the operator's
healthchecks.io account (the ping URL is in OpenBao under `kv/eso/prd/prometheus/prd/`).

1. [ ] Does the cluster answer? `kubectl -n prometheus-prd get pods`
2. [ ] It does, and Prometheus or Alertmanager is not Running :: none written; describe the pod
3. [ ] It does not :: [Estate down](estate-cold-boot.md), and [No DHCP or DNS](no-dhcp-dns.md) once leases start running out

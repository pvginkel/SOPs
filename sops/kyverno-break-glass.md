---
title: Kyverno refuses new pods
kind: emergency
project: Ansible
when: >-
  New pods on prd are not created: rollouts stall, Jobs start nothing, and the FailedCreate events
  name the webhook mpol.validate.kyverno.svc-fail.
---

Kyverno's admission controller (`kyverno-prd`, three replicas) sets each new pod's memory request
on prd. Its pod webhook fails closed, so while no replica answers, every pod create in a covered
namespace is refused. Running pods are untouched. The break-glass deletes Kyverno's mutating
webhook registration: pods are then created without Kyverno until it registers again.

The commands are the Ansible Kyverno runbook's
[Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/kyverno.md#break-glass),
mirrored on this site. This card is the order, and what to have on the desk.

## Identify

| You see | Do |
|---|---|
| `failed calling webhook "mpol.validate.kyverno.svc-fail"` in a ReplicaSet's, Job's or StatefulSet's `FailedCreate` events | Kyverno isn't answering. Restore below |
| `admission webhook "mpol.validate.kyverno.svc-fail" denied the request` | Kyverno answers with an error from its policy. Restore below brings pod creation back too; the fix is in KyvernoDeploy's policy |
| Pods missing in `kube-system`, `metallb-system`, `argocd-prd`, `argocd-hooks` or `kyverno-prd`, or a KubeCoder environment pod | Not this card: the webhook never sees those pods |
| A pod started with a memory request you didn't expect | Not this card: [Which request a pod got](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/kyverno.md#which-request-a-pod-got-and-why) |

## Before you start

1. [ ] Write access :: `~/.kube/config-prd-write`. The default kubeconfig can't delete a webhook
   registration.
2. [ ] API token or apiserver VIP broken :: `ssh ansible@srvk8s1 sudo microk8s kubectl …` on a
   control-plane node, by IP if DNS is down too
   ([cold-boot.md § Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md#break-glass),
   "SSH by IP").
3. [ ] The probe :: the runbook's server-side dry run of a pod in `development`. It prints
   `pod/kyverno-probe` when admitted and the webhook's error when refused, and creates nothing.

## Restore

1. [ ] Probe :: refused, naming `mpol.validate.kyverno.svc-fail`.
2. [ ] Delete the registration :: `kyverno-resource-mutating-webhook-cfg`. Note the UTC time.
3. [ ] Back within seconds :: Kyverno is running but not answering; its leader rewrites the
   registration every 10 seconds. Scale `kyverno-admission-controller` in `kyverno-prd` to 0: a
   replica that shuts down cleanly deletes the registration itself. Once its pods are gone, delete
   the registration again if it still stands.
4. [ ] Probe :: admitted.

## Afterwards

1. [ ] Fix Kyverno :: neither `kyverno-prd` nor `argocd-prd` is refused, so a fix pushed to
   KyvernoDeploy syncs as usual.
2. [ ] Scaled to 0 in step 3 :: scale `kyverno-admission-controller` back to 3. With `selfHeal`
   off, Argo leaves it at 0 until then or until KyvernoDeploy syncs.
3. [ ] Registration back :: once a replica leads, `kyverno-resource-mutating-webhook-cfg` with
   entry `mpol.validate.kyverno.svc-fail` and owner `kyverno-prd:webhook`. The probe is admitted.
4. [ ] Pods created since the noted time :: they kept the request they arrived with, none or their
   limit. List them and `kubectl rollout restart` the workloads that should not wait for their
   next pod.

The runbook's [Drilling it](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/kyverno.md#drilling-it)
rehearses this card with Kyverno healthy.

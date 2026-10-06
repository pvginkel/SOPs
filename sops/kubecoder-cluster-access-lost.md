---
title: KubeCoder lost cluster access
kind: emergency
project: KubeCoder
when: >-
  Every environment's kubectl is refused at once, on both contexts, and so is the controller's:
  after a cluster rebuild, or after the kubecoder ServiceAccounts or their token Secrets in
  kube-system were deleted.
order: 40
---

The procedure is KubeCoder's
[Re-minting KubeCoder's cluster identities](https://github.com/pvginkel/KubeCoder/blob/main/docs/operations/cluster-identity-remint.md).
This card gets you there with the right things on the desk.

Every environment's `~/.kube` rests on two ServiceAccounts per cluster, `kubecoder-ro` and
`kubecoder-rw` in `kube-system`, and their non-expiring token Secrets: minted by hand, reconciled
by nothing. Three kubeconfigs are built from them (`config` merges both clusters,
`config-dev-write`, `config-prd-write`), held in two OpenBao leaves
(`eso/prd/kubecoder/prd/catalog` and `eso/prd/kubecoder/dev/catalog`), extracted by ESO, and
mounted into each env pod once, at its start.

## Identify

| You see | Go to |
|---|---|
| The prd cluster was rebuilt empty | [Workloads on a rebuilt cluster](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cluster-bootstrap.md) first; this procedure is its "Afterwards" |
| srvk8sdev was replaced | [Rebuild srvk8sdev](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/k8s-rebuild.md#rebuild--srvk8sdev-single-node-dev) first, then the dev half of the procedure. The base `config` merges both halves, so every environment is affected, not only `--context dev` |
| The ServiceAccounts, bindings or token Secrets were deleted on a running cluster | The procedure from step 1, for that cluster only |
| Only `kubectl --context dev` fails; prd is fine | srvk8sdev is off by default (`onboot: 0`). Not this card |
| `argocd` in environments is refused while kubectl works | Argo's `kubecoder` account token: [argocd.md](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#the-kubecoder-accounts-token) |

## Before you start

1. [ ] You cannot use KubeCoder to fix KubeCoder :: every `kubectl` runs as `sudo microk8s kubectl`
   over SSH on a node, `ansible@srvk8s1` for prd and `ansible@srvk8sdev` for dev, from wrkdev.
   The SSH option pile is in Ansible
   [`live-infra-access.md`](https://github.com/pvginkel/Ansible/blob/main/docs/live-infra-access.md#what-still-needs-ssh).
2. [ ] Both clusters up :: neither half is optional. srvk8sdev is VM 919 on `pve` and off by
   default: start it first.
3. [ ] A KubeCoder checkout :: the read role is `docs/operations/kubecoder-ro-read.yaml`, streamed
   into the node's `kubectl apply -f -`.
4. [ ] The apiserver addresses :: the one value no cluster read yields. They are in the doc's
   table; never lift them from the node's own admin config.
5. [ ] OpenBao admin :: `bao` logged in with the `openbao-admin` AppRole
   ([openbao.md § Admin access](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#1--admin-access))
   to `kv patch` both catalog leaves. `patch`, never `put`: each leaf holds the stage's other
   catalog keys too.
6. [ ] A way to restart every running environment :: KubeCoder's own restart (the Telegram bot's
   restart control, or the MCP `restart` tool). Never `kubectl delete pod`: nothing recreates an
   environment's pod, so that leaves the fleet stopped with the right files.

## Then

Work the doc top to bottom: ServiceAccounts, bindings (one recipe per cluster, they are not
mirror images: prd's `kubecoder-rw` is `cluster-admin`, dev's is `edit`), token Secrets of the
non-expiring kind, the three files (a rebuild changes the CA, so it is never a token-only swap),
both catalog leaves, then the env pods. Finish with its "Verifying the finished state".

!!! note "Not rehearsed"
    The doc says so itself: re-minting identities on a working cluster to prove a document is not
    worth the risk. Read the whole page before the first command.

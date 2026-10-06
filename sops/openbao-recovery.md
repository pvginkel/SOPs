---
title: OpenBao is down, or a secret is needed without it
kind: emergency
project: Ansible
when: >-
  An srvvault node or the whole OpenBao cluster is lost, or a secret has to be read while
  there is no cluster to read it from.
---

The procedures themselves are the Ansible OpenBao runbook, mirrored on this site. This card gets
you to the right section with the right things on the desk.

## Identify

| You see | Go to |
|---|---|
| One `srvvaultN` gone. The other two hold quorum and clients are fine | [Single-node loss](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#2--single-node-loss) |
| All three gone at once | [Whole-cluster loss](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#3--whole-cluster-loss) |
| One secret needed, and no cluster to ask | [Break-glass](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#4--break-glass-read-a-secret-without-a-cluster) |
| srviac's `iac` won't start because OpenBao is down | [IaC agent cold boot](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-cold-boot.md) |
| Everything restarted at once (a power cut) | [Estate cold boot](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/cold-boot.md) |

New hardware (fire, theft, nothing left): OpenBao is not first. The order is on
[Estate down, or a power cut](estate-cold-boot.md).

## Before you start

1. [ ] Roboform :: the ansible-vault passphrase, the Shamir recovery keys (3 of 5), the age backup key
2. [ ] An Ansible checkout :: `git clone https://github.com/pvginkel/Ansible`, then `poetry install`
3. [ ] On the machine you work from :: `bao`, `age`, `jq`, `terraform`, SSH to the PVE hosts
4. [ ] If `openbao_ufw_enable` is on :: srvvaultN takes SSH from srviac only, so work from there
5. [ ] Whole-cluster loss only: the newest backup :: `openbao/<ts>_openbao-backup.tgz.age` at
   `backupServer.rcloneRemote` (StorageDeploy `config/prd/values.yaml`)

## Then

Work the runbook section top to bottom. A whole-cluster recovery does not end at the snapshot
restore. The restore brings every AppRole back with the secret_ids it held at the snapshot, so
steps 5 to 8 re-issue the ones whose consumers are now rejected: `openbao-admin` from a root
token minted with the Shamir keys, then `iac-agent`, then `backup`, then every rotation made
since the snapshot. Step 9 verifies.

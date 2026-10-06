---
title: Restore drills, yearly
kind: periodic
project: Ansible
when: >-
  Once a year, and after a change to a backup path. A round restores every backup somewhere
  harmless and proves the result is usable.
---

The procedures and their Drill logs are the Ansible runbooks, mirrored on this site. This card is
the round: every drill once, then a row in the run log below. Nothing announces that the year is
up.

## Before you start

1. [ ] Roboform :: the age private key, the s3-mirror crypt password and salt, the Shamir
   recovery keys (3 of 5), the ansible-vault passphrase
2. [ ] The Google Drive login, for `gdrive-pieter:Homelab Backups`
3. [ ] A host with rclone, age, Docker, kubectl, jq and a browser. The KubeCoder pod does not
   qualify: it has no rclone or Docker.
4. [ ] For the S3 mirror :: srvk8sdev (VM 919 on `pve`, off by default) can be started
5. [ ] For YouTrack :: a local YouTrack administrator's password
6. [ ] Each drill the morning after a successful nightly run of its backup, so production has
   changed as little as possible since

## The round

1. [ ] OpenBao, whole-cluster loss :: [openbao.md §3](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#3--whole-cluster-loss)
   on the real srvvault VMs, through the re-issue of every AppRole, to its step 9. Record the
   timings in its [Drill log](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#drill-log).
   Last drilled 2026-05-23.
2. [ ] OpenBao, single-node loss :: [openbao.md §2](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#2--single-node-loss):
   replace one srvvaultN, let the roles converge, watch Raft stream the snapshot from the leader.
   Never drilled; its timings are the TBD in the Drill log.
3. [ ] S3 mirror :: [s3-mirror.md §5](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/s3-mirror.md#5--restore-drill):
   `iot-prd-attachments` from Drive into a scratch bucket on srvk8sdev, checked byte for byte
   against the live bucket. Record it in its [Drill log](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/s3-mirror.md#drill-log).
   First drill still owed.
4. [ ] YouTrack :: [youtrack-restore.md §3](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/youtrack-restore.md#3--restore-drill):
   the newest Drive backup into a throwaway container, with the chart's start arguments. Record it
   in its [Drill log](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/youtrack-restore.md#drill-log).
   First drill still owed.
5. [ ] Add a row per drill to the run log below.

!!! warning "Backed up, but nothing to drill"
    The `postgres-pas` dumps (90 kept on Drive, nightly `pg_dump` through `backup-server`) and
    the PVE vzdump of the VMs on `pve` (`local-backup`, retain three) have no restore procedure
    written. Until one exists they are not on this card, and a complete round does not prove them.

## Run log

| Date | Drill | Result | Log |
|---|---|---|---|
| 2026-05-23 | OpenBao, whole-cluster loss (a single drill, before this card) | Pass: converge 6m32s, restore and verification about 5 min more | [openbao.md Drill log](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#drill-log) |

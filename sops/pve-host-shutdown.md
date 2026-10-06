---
title: Shutting down a PVE host
kind: normal
project: Ansible
when: Before powering off pve, pve1 or pve2.
---

One host at a time. Each PVE host carries one member of every three-node cluster (the k8s control
plane, Ceph, OpenBao), and each cluster survives losing one. Which VM lives where: `pve_node` in
Ansible [`terraform/prd/vms.tf`](https://github.com/pvginkel/Ansible/blob/main/terraform/prd/vms.tf).

## Before

1. [ ] Know what goes down with it :: `qm list` on the host
2. [ ] A Ceph node on it :: `ceph osd set noout`
3. [ ] srvk8s1/2/3 on it: cordon the node, then `kubectl rollout restart` every
   `iac.webathome.org/pre-drain=true` Deployment running there (today keycloak-prd and
   keycloak-dev) and wait for Ready. Then drain it:

    ```
    kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --timeout=300s
    ```

    CNPG moves the Postgres primary off the node by itself.

4. [ ] srvk8s4 on it (it lives on `pve`): don't drain. Its taint and pinned volumes mean nothing
   can move. It hosts every KubeCoder environment, so commit and save your work first.

!!! note "Down for the whole window when it's `pve`"
    zpool2 workloads (storage and its Samba share, mydownloads, prometheus-server), srviac,
    Home Assistant, wrkdev, wrkdevwin. srvk8sdev has `onboot=0` and stays off.

## After

1. [ ] Drained node :: `kubectl uncordon <node>`
2. [ ] Ceph :: `ceph osd unset noout`
3. [ ] Ceph health :: `HEALTH_OK`
4. [ ] OpenBao unseals and rejoins by itself. Check that all three name the same leader:

    ```
    for n in 1 2 3; do curl -sk https://srvvault$n.home:8200/v1/sys/leader; echo; done
    ```

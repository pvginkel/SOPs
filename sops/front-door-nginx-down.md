---
title: Front-door nginx down
kind: emergency
project: Ansible
when: >-
  Every .home, webathome.org and ginbov.nl host is unreachable at once while the cluster is up;
  or LoadBalancerNotAnnounced names nginx-prd/nginx.
order: 30
---

One nginx (`nginx-prd/nginx`, one replica, MetalLB `10.2.1.7`) fronts every `.home`,
`webathome.org` and `ginbov.nl` host: the apps, Keycloak, Argo CD's UI and webhook relay,
Jenkins, and KubeCoder. `nginxmanager` (container `nginx-configurator`) watches every Service
carrying `nginx.webathome.org/*` annotations, 94 today, each KubeCoder environment's front
Services among them, writes the generated config onto nginx's volume and **restarts** the nginx
Deployment: a rollout, not a reload. A config nginx can't load reaches it at that restart.

!!! note "Re-verified 2026-10-06"
    NginxDeploy deploys through Argo CD (`nginx-prd`, auto-sync, no self-heal).
    `server_names_hash_bucket_size` is 128 since the 2026-08-19 outage
    (`chart/files/conf.d/10-http-configuration.conf`), so a long environment hostname no longer
    kills nginx by itself; the longest name today is 50 characters. Jenkins is still ClusterIP-only
    and reached only as `jenkins.webathome.org` through this nginx. A webhook relay exists now, at
    `deploy-hooks.webathome.org`, behind this nginx too.

## Identify

| You see | Do |
|---|---|
| The nginx pod isn't Running, or its log says `could not build server_names_hash` or otherwise refuses the config | A generated config nginx can't load. Find the Service annotated last and delete it: Restore below |
| The pod is Running; `LoadBalancerNotAnnounced` names `nginx-prd/nginx` | MetalLB withdrew `10.2.1.7`. The alert's description is the procedure: the EndpointSlice ready, `describe svc` for the address, then the speakers' logs in `metallb-system` |
| One host unreachable, the rest fine | Not this card. `nginx-configurator`'s log names the Service or certificate at fault |

## Before you start

1. [ ] Work from wrkdev, or a shell on srvk8s1 :: KubeCoder's own front door is this nginx (its
   controller Service carries the same annotations), so don't count on reaching an environment.
   `ssh ansible@srvk8s1 sudo microk8s kubectl …` always works.
2. [ ] Write access :: `~/.kube/config-prd-write`; the default kubeconfig can't delete in
   `kubecoder-prd`. `sudo microk8s kubectl` on a node has it.
3. [ ] Nothing ships through Jenkins or a GitHub webhook while nginx is down :: both sit behind
   it. Restore out of band first, then the durable fix.

## Restore

1. [ ] The pod and its log:

    ```
    kubectl -n nginx-prd get pods
    kubectl -n nginx-prd logs deploy/nginx --tail=50
    ```

2. [ ] Which Service's annotation did it :: the newest ones are at the bottom

    ```
    kubectl get svc -A --sort-by=.metadata.creationTimestamp \
      -o custom-columns='CREATED:.metadata.creationTimestamp,NAMESPACE:.metadata.namespace,NAME:.metadata.name,SERVER-NAME:.metadata.annotations.nginx\.webathome\.org/server-name' \
      | grep -v '<none>' | tail
    ```

3. [ ] Delete the Service, not the environment :: `kubectl -n kubecoder-prd delete svc <name>`.
   KubeCoder converges an environment's front Services only at its bring-up (a start or a
   restart), so the deletion sticks and the environment keeps running with no work lost.
4. [ ] Watch the configurator rewrite and restart :: it logs `Writing configuration`,
   `Updating configuration`, `Restarting NGINX`.

    ```
    kubectl -n nginx-prd logs deploy/nginxmanager -c nginx-configurator --tail=20
    ```

5. [ ] nginx Running and a `.home` host answering again.

## Afterwards

1. [ ] The durable fix in NginxDeploy :: push to `main`. Its webhook was lost while nginx was
   down; Argo polls every 30 minutes, or refresh it by hand:
   [Webhooks](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#webhooks).
2. [ ] Jenkins :: a push whose GitHub webhook landed while nginx was down is lost, and GitHub
   does not retry. Build by hand.
3. [ ] The deleted front Service :: comes back at that environment's next start. If its hostname
   was the cause, fix the cause before then.

Background: the 2026-08-19 outage (a 50-character environment hostname against nginx's 64-byte
default bucket), recorded only in agent memory until this card; NginxDeploy's
[README](https://github.com/pvginkel/NginxDeploy/blob/main/README.md); the alert in
PrometheusDeploy `config/prd/values.yaml`, group `loadbalancers`.

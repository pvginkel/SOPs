---
title: Bump Keycloak's version
kind: periodic
project: Ansible
when: >-
  A new Keycloak release to take. On 2026-11-21: 26.7.3 on keycloak-prd (auth.ginbov.nl, realm
  homelab) and keycloak-dev (keycloak-dev.home, realm homelab-dev), one image for both.
---

The version is `KEYCLOAK_VERSION` in DockerImages
[`keycloak/build-matrix.json`](https://github.com/pvginkel/DockerImages/blob/main/keycloak/build-matrix.json).
A push of it to DockerImages `main` rolls both stages with no stop between. The `DockerImages` job
builds the image and commits its tag to HomelabAppsDeploy `keycloak/config/prd/values.yaml` and
`keycloak/config/dev/values.yaml`, and Argo CD syncs both stages from `main`. Keycloak runs one
pod with `Recreate`, so sign-in is down while it restarts.

An adopted app is one whose deploy repo's Terraform declares its Keycloak clients. It logs in to
`homelab` as `argocd-hook` on every sync and plan Job, so while Keycloak is down or refuses that
login, the app's sync waits. The convention and the hook's credential are in the runbook
[Add an OIDC client to an app](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/oidc-client.md).

## Before

1. [ ] Upgrade notes :: [Upgrading Keycloak](https://www.keycloak.org/docs/latest/upgrading/),
   every "Migrating to" section after the live version, up to the target. A change to the Admin
   REST API or to service-account clients reaches every adopted app's hook.
2. [ ] The provider :: the
   [provider's issues](https://github.com/keycloak/terraform-provider-keycloak/issues) that name
   the target version. A bump that needs a newer provider takes it first, per the runbook's
   [§ The provider's version](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/oidc-client.md#the-providers-version).
3. [ ] Crossing 26.8.2 :: [§ Crossing 26.8.2](#crossing-2682-the-admin-api-scope) is owed as
   soon as Keycloak answers. Have both admin consoles open before you push.

## Bump

1. [ ] `KEYCLOAK_VERSION` :: edit `keycloak/build-matrix.json`, commit, push DockerImages `main`
2. [ ] The roll :: the `DockerImages` build is green, its pin commit is on HomelabAppsDeploy
   `main`, and `keycloak-prd` and `keycloak-dev` are Synced and Healthy at it
3. [ ] Sign in :: to an app through Keycloak, such as pgAdmin

## Crossing 26.8.2: the Admin API scope

!!! danger "Every adopted app's sync fails until argocd-hook has the scope"
    From 26.8.2 the Admin REST API answers `401` to a token without the `kc-admin-api` scope
    ([Migrating to 26.8.2](https://www.keycloak.org/docs/26.8.2/upgrading/)). The upgrade
    creates the scope in every realm and gives it to `admin-cli` and `security-admin-console`
    alone. The scope does not exist before the roll, so the clients get it right after.

A client whose service account holds a `realm-management` role calls the Admin API. In the
realm's admin console, give each one the scope: Clients, the client, Client scopes, Add client
scope, `kc-admin-api`, **Default**. The client's next login takes a token that carries it.

1. [ ] `homelab` :: `argocd-hook`, `iotsupport-admin`, `secret-rotator` once SecretRotator's go-live
   has made it, and `keycloak-review-readonly` while it exists
2. [ ] `homelab-dev` :: `iotsupport-admin`, `secret-rotator` once SecretRotator's go-live has made
   it, and `keycloak-review-readonly` while it exists
3. [ ] Reading :: a plan Job of an adopted app at `main` reads
   `presync: the plan carries no changes`
   ([§ Planning a stage's Terraform](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#planning-a-stages-terraform-as-its-hook-applies-it)).
4. [ ] Retries ran out :: sync again by hand each adopted app whose sync failed in the window
   ([§ Diagnosing a failed sync](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#diagnosing-a-failed-sync)).

## After the roll: the provider blocks

Each adopted app's `terraform/providers.tf` sets `keycloak_version` to the version Keycloak runs,
as a literal. Keycloak withholds its version from an admin client confined to one realm.

1. [ ] Find them :: `grep -l keycloak_version */terraform/providers.tf` in HomelabAppsDeploy and
   PlatformAddOnsDeploy, and `terraform/providers.tf` in each dedicated deploy repo.
2. [ ] Bump :: set `keycloak_version` to the new version in each, one commit per repo, on a topic
   branch
3. [ ] Plan before it lands :: a plan Job at the branch's SHA reads
   `presync: the plan carries no changes` for each stage it touches. Then fast-forward `main`.
   This is the runbook's rule that every commit is planned before it lands.

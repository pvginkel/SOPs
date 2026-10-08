---
title: Annual rotation of the bootstrap-tier secrets
kind: periodic
project: Ansible
when: >-
  Once a year, or at once on suspicion that a workstation or Roboform is compromised. Nothing
  announces it yet: SecretRotator's catalog lists the tier at interval `never`.
---

The bootstrap tier is what OpenBao cannot hold because it gates OpenBao or decrypts the repo.
SecretRotator's inventory names six, the markers `rotator/bootstrap/*` in AnsibleSpecs
`secret-rotation/catalog.md`. Four rotate on this card; the seal key and the backup age key
rotate only on compromise (end of card). The vault rekey comes first, so everything re-vaulted
after it lands under the new passphrase.

## Before you start

1. [ ] Roboform :: the "operator workstation" entry (the ansible-vault passphrase),
   `homelab-ca JWK provisioner password`, the GitHub login
2. [ ] A checkout with the vault unlocked :: `ANSIBLE_VAULT_PASSWORD_FILE` pointing at
   `ansible/.vault_pass`, per [operator-workstation.md](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/operator-workstation.md#ansible-vault-passphrase)
3. [ ] SSH to srviac, to edit `/etc/iac/secrets.yaml` (layout: [`secrets.example.yaml`](https://github.com/pvginkel/Ansible/blob/main/support/iac-agent/etc/iac/secrets.example.yaml))
4. [ ] A window with no `IaC/Scheduled *` job due. `IaC/Apply`, `IaC/Scheduled Drift` (daily,
   `H 11`) and `IaC/Scheduled Certs` (Fridays, `H 4`) run Ansible on srviac and read vaulted
   values; while the repo and srviac disagree on the passphrase, they fail.

## 1. The ansible-vault passphrase

!!! warning "Not yet exercised"
    No rekey has been run on this repo. Three files are vaulted: `roles/openbao/files/static.key`
    whole, and four inline `!vault |` values in `inventories/prd/group_vars/all/vips.yml`
    (`vrrp_auth_password`, `internal_tls_jwk_provisioner_password`) and
    `inventories/prd/group_vars/openbao.yml` (`openbao_admin_role_id`,
    `openbao_admin_secret_id`). `ansible-vault rekey` takes the
    whole-file vault; the inline values are re-encrypted one by one with `encrypt_string`, the
    form each file's own header gives. Paths below are under `ansible/`.

1. [ ] New passphrase :: at least 20 random characters or 8 diceware words. Save it in Roboform
   as a second entry marked `(new)` until step 10.
2. [ ] With the **old** passphrase still in `.vault_pass`, read each inline value back. One at a
   time, the shape [openbao.md §1](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#1--admin-access)
   uses; keep the output in a file under `/dev/shm/`, nowhere else:

    ```
    cd ansible && poetry run ansible srvvault1 -m debug -a 'msg="{{ <variable> }}"'
    ```

3. [ ] Rekey the whole-file vault. The old passphrase comes from `ANSIBLE_VAULT_PASSWORD_FILE`;
   type the new one at its prompt:

    ```
    poetry run ansible-vault rekey roles/openbao/files/static.key
    ```

4. [ ] Switch `.vault_pass` to the new passphrase, typed at a hidden prompt so it stays out of
   the shell history: `read -rs NEW && printf '%s' "$NEW" > .vault_pass && unset NEW`.
5. [ ] Re-encrypt each of the five values under the new passphrase and replace its `!vault |`
   block in the file. Paste the value at the hidden prompt, never on the command line:

    ```
    read -rs VALUE && printf '%s' "$VALUE" | poetry run ansible-vault encrypt_string --stdin-name <variable>; unset VALUE
    ```

6. [ ] Prove it: step 2's read of each variable again, now under the new passphrase. Then
   `shred -u` the scratch file. `git diff` must touch only the three vault files. Commit; do
   not push yet.
7. [ ] srviac :: in `/etc/iac/secrets.yaml`, the `files:` entry `/etc/iac/ansible_vault_pass`
   gets the new passphrase as its `content:`. No restart: every `iac` run reads the file fresh.
8. [ ] Push. `IaC/Build-Main` runs by itself. Then start `IaC/Scheduled Drift` by hand: it
   converges nothing, and a vault error there means the repo and srviac disagree.
9. [ ] KubeCoder :: the catalog key `ansible-vault-password` in
   `kv/eso/prd/kubecoder/prd/catalog` is what every Ansible environment reads at start as
   `/run/secrets/ansible-vault-password`. `patch`, never `put`: `put` replaces the bag whole
   ([argocd.md](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#the-kubecoder-accounts-token)
   does the same for another key). With the passphrase in `$VALUE` from `read -rs VALUE`, never on
   the command line:

    ```
    . scripts/bao-login.sh && printf %s "$VALUE" | cexec iac bao kv patch -mount=kv eso/prd/kubecoder/prd/catalog ansible-vault-password=-
    cexec iac kubectl --kubeconfig ~/.kube/config-prd-write --context prd annotate externalsecret -n kubecoder-prd kubecoder-secret-catalog force-sync=$(date +%s) --overwrite
    ```

    Then `kc env restart` each Ansible environment: a running one keeps the old passphrase until
    it restarts. One that still has `~/.ansible/vault-pass` holds the old passphrase in plain
    text; delete it.

10. [ ] Roboform :: the "operator workstation" entry gets the new passphrase; delete the `(new)`
    copy. Any other workstation with an `ansible/.vault_pass` gets it too.

## 2. JWK provisioner password

1. [ ] [step-ca-bootstrap.md § JWK provisioner password rotation](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-bootstrap.md#jwk-provisioner-password-rotation):
   new password, re-encrypt the provisioner on the CA, re-vault
   `internal_tls_jwk_provisioner_password`, force one re-issue, update Roboform.

## 3. GitHub PAT for TerraformState

1. [ ] [iac-agent.md § `GIT_API_TOKEN`](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#git_api_token-github-pat-for-terraformstate):
   mint a PAT with the same scope (`repo` classic, or `Contents: Read and write` on
   `TerraformState`), paste it into `/etc/iac/secrets.yaml` on srviac. No restart.
2. [ ] Revoke the old PAT at GitHub.

## 4. Jenkins inbound-agent secret

1. [ ] [iac-agent.md § `JENKINS_AGENT_SECRET`](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/iac-agent.md#jenkins_agent_secret):
   regenerate on the controller, paste into `/etc/iac/secrets.yaml`, `systemctl restart
   jenkins-agent` on srviac.

## 5. Record it

1. [ ] Once SecretRotator is live: stamp each marker, so the inventory shows the
   rotation. Its plan is one `operator.confirm`; the value never enters OpenBao
   ([openbao.md §5](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#5--rotation)):

    ```
    ssh -t ansible@srviac "sudo iac -c 'secret-rotator run rotator/bootstrap/<marker>'"
    ```

2. [ ] Add a row to the run log below.

!!! note "Not on this card"
    **The static seal key.** Rotation is a seal migration on all three srvvault nodes, sketched
    in [openbao.md §5](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#5--rotation)
    and never written out: new key, bump `openbao_seal_current_key_id`, the old key id declared
    until every node has migrated. On compromise only.

    **The backup age key.** Its private half lives only in Roboform; every kept backup (OpenBao,
    `postgres-pas`, YouTrack) is encrypted to the public half in `backup-server`'s
    `backup-server-age-key` ConfigMap. A rotation keeps the old private key until those age out.
    No procedure exists. On compromise only. The Terraform state age key is a different key,
    `kv/iac/tf-backend`, and re-encrypting every state is a project, not a rotation.

## Run log

| Date | Rotated | Notes |
|---|---|---|
| — | none yet | the vault rekey has never been exercised |

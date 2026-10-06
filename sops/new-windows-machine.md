---
title: New Windows machine
kind: normal
project: Ansible
when: A new Windows machine or VM the operator will use against homelab URLs.
---

What to do, in which order. The certificate comes first: the homeapps extension downloads over
`https://homeapps.home`, and Chrome refuses it from a machine that does not trust the homelab CA.

## Steps

1. [ ] Trust the homelab CA ::
   [step-ca-bootstrap.md § Windows trust install](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-bootstrap.md#windows-trust-install).
   The root is Ansible `ansible/roles/baseline/files/homelab-root.crt`; `certutil` from an
   elevated PowerShell, then check `certmgr.msc`.
2. [ ] Firefox ::
   [§ Firefox](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-bootstrap.md#firefox):
   the `security.enterprise_roots.enabled` flag, or a per-profile import
3. [ ] Smoke test ::
   [§ Per-machine smoke test](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/step-ca-bootstrap.md#per-machine-smoke-test):
   `https://ca.home/health` clean in Chrome and Firefox
4. [ ] homeapps, force-installed through Chrome Browser Cloud Management :: Home
   [`docs/cbcm-runbook.md`](https://github.com/pvginkel/Home/blob/main/docs/cbcm-runbook.md)
   §3 (two registry values under `HKLM\SOFTWARE\Policies\Google\Chrome`) and §4 (verify:
   `chrome://management` says managed, `chrome://extensions` shows homeapps installed by policy).
   On the desk: local admin, the extension ID from `curl -s https://homeapps.home/ext/info`, and
   the enrollment token from the Google Admin console (Devices → Chrome → Managed Browsers) under
   the managed `webathome.org` account. Then fully restart Chrome.

!!! note "One-time setup is done elsewhere"
    Home [`README.md` § Operator one-time setup](https://github.com/pvginkel/Home/blob/main/README.md#operator-one-time-setup-force-install)
    is per deployment, not per machine: the signing key in OpenBao at
    `eso/prd/homeapps/extension-signing` and the force-install entry it yields. The CBCM
    runbook's §1–2 (the managed Google account, the enrollment token) are one-time too. Whether
    CBCM enrollment is in place today is not written down; `chrome://management` on a machine
    that already has homeapps says.

!!! note "Not written down"
    The operator's personal setup on Windows — SSH keys, Roboform, the VSCode Remote-SSH hop into
    srviac that AnsibleSpecs `decisions.md` names as the OpenBao admin path — has no runbook.

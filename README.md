# Homelab QRH

The homelab's standard operating procedures, published as a Quick Reference Handbook at
**https://pvginkel.github.io/SOPs/**.

An SOP is a procedure done by hand when something triggers it: after a release, before powering
off a host, when a cluster is lost. It is short enough to follow as a checklist, and it can come
from any project. The site is on GitHub Pages so that it is still there when the homelab is not.

The site also mirrors the Ansible runbooks (`docs/runbooks/` in
[pvginkel/Ansible](https://github.com/pvginkel/Ansible)). They stay in Ansible, next to the code
they describe; the mirror is rebuilt on every push here and once a day. An SOP that needs a
runbook links to it instead of copying its steps.

## Writing an SOP

One Markdown file per SOP in `sops/`, named after what it does. It starts with front matter:

```yaml
---
title: Shutting down a PVE host
kind: normal          # emergency | abnormal | normal | periodic
project: Ansible      # the project it belongs to, shown as a chip
when: Before powering off pve, pve1 or pve2.
order: 10             # optional: position within its kind; the default sorts by title
---
```

| Kind | Tab | For |
|---|---|---|
| `emergency` | red | something is down and has to come back |
| `abnormal` | amber | something is degraded or wrong, but nothing is down yet |
| `normal` | green | planned operations: maintenance, shutdowns, changes |
| `periodic` | blue | chores triggered by an outside event: a release, a model change |

The body is CommonMark with tables, plus:

- **Steps.** A list item that starts with `[ ]` is a step, with a checkbox to tick. The page keeps
  ticks for a day, so a reload or a lost tab does not lose your place.
- **Challenge and response.** In a step, `Ceph :: ceph osd set noout` renders as
  `Ceph ........ ceph osd set noout`, QRH style. Keep it for short items.
- **Callouts.** `!!! note "Title"`, `!!! warning "Title"` or `!!! danger "Title"`, with the
  content indented four spaces.
- **Links.** Link a runbook by its GitHub URL
  (`https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/openbao.md#3--whole-cluster-loss`).
  It still works when the file is read on GitHub, and on the site it goes to the mirrored page.
  Another SOP is a relative link: `pve-host-shutdown.md`.

The repo is public. Name where a secret lives, never the secret.

## Building

```sh
poetry install
poetry run python site/build.py --ansible ../Ansible --out _site
```

Open `_site/index.html` straight from disk; every link is relative. The build fails on bad front
matter and on a broken link in an SOP. A broken link in a mirrored runbook prints a warning, since
Ansible owns the fix.

Every page links to `qrh-offline.zip`, the whole site in one file, for the day GitHub is down too.

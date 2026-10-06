# CLAUDE.md

The Homelab QRH: the operator's standard operating procedures, built into a static site and
published on GitHub Pages at https://pvginkel.github.io/SOPs/. [`README.md`](README.md) has the
SOP format: front matter, kinds, steps, callouts and links. Read it before writing one.

- **What belongs here.** A procedure done by hand when a trigger fires, from any project. The
  operator's standing rule: SOPs go here. A repo's runbooks stay in that repo. The Ansible ones
  are mirrored onto the site at build time; link them from an SOP, never copy their steps.
- **Public repo.** Never put a credential, a token or a secret value in an SOP. Say where it lives
  (Roboform, an OpenBao path) instead.
- **Gates.** `kc project test` builds the site and fails on a broken SOP link or bad front matter.
  `kc project lint` runs ruff over `site/`.
- **Publishing.** A push to `main` publishes the site through `.github/workflows/pages.yml`. Ask the
  operator before pushing.
- **Style.** The site is a cockpit Quick Reference Handbook on purpose: colored section tabs,
  dotted challenge-response leaders, "End of procedure". Keep new UI in that spirit, and keep it
  dependency-free and working from `file://`, because the offline copy depends on it.

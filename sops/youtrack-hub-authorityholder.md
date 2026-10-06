---
title: YouTrack Hub calls fail with "Item of type AuthorityHolder … is not found"
kind: abnormal
project: Ansible
when: >-
  Every Hub API call on issues.webathome.org fails with that error while YouTrack's own `/api/*`
  keeps working.
---

A stale reference in Hub's permission cache, not in the database. On 2026-09-16 a `<project>
admins` group was deleted through `DELETE /hub/api/rest/usergroups/{id}`; the project's Team group
kept pointing at it and every Hub call from the token's account failed, even after recreating the
group under its old id. API repairs do not help. A restart of the YouTrack pod fixed it
completely.

YouTrack is one replica with strategy `Recreate`, so the restart is about a minute of downtime
(43 s to `YouTrack init complete` on 2026-09-17). It needs `~/.kube/config-prd-write`.

## Steps

1. [ ] Confirm it is Hub, not YouTrack. With an admin token (`YOUTRACK_TOKEN` in a
   YouTrackMCPServer environment):

    ```
    curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $YOUTRACK_TOKEN" \
      'https://issues.webathome.org/hub/api/rest/users?fields=login'
    kubectl -n youtrack-prd logs deploy/youtrack --since=10m | grep -E 'ERROR|AuthorityHolder'
    ```

2. [ ] Restart, and wait for the new pod:

    ```
    kubectl -n youtrack-prd rollout restart deploy/youtrack
    kubectl -n youtrack-prd rollout status deploy/youtrack
    ```

3. [ ] `YouTrack init complete` :: in the pod log
4. [ ] The curl of step 1 :: `200`, and no new `AuthorityHolder` line

!!! warning "Don't"
    Never delete Hub users or groups on this instance directly. The import creates `<project>
    admins` groups and reuses them: leave them. Hub Integration's quick fixes are untested
    production writes; the runbook below has them, behind a database backup.

## Runbooks

In YouTrackMCPServerSpecs (private):

- [Hub Integration diagnostics and quick fixes](https://github.com/pvginkel/YouTrackMCPServerSpecs/blob/main/docs/runbook-hub-quick-fixes.md):
  the Hub Integration page, its four jobs, and the three open mapping findings. Its § Procedure
  step 6 is this card.
- [A project stuck pending deletion](https://github.com/pvginkel/YouTrackMCPServerSpecs/blob/main/docs/runbook-stuck-project-deletion.md):
  the restart command and its downtime, and the other reason to restart YouTrack.

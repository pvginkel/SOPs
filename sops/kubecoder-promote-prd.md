---
title: Promote KubeCoder to prd, or roll it back
kind: normal
project: KubeCoder
when: >-
  A change validated on dev goes to prd, or a prd regression has to be reverted.
---

The procedure is KubeCoder
[deploy-operations.md § Path 2](https://github.com/pvginkel/KubeCoder/blob/main/docs/operations/deploy-operations.md#path-2--promote-prd-promotes-a-commit-on-main-to-prd);
what the job refuses is KubeCoderDeploy
[README § Promotion](https://github.com/pvginkel/KubeCoderDeploy/blob/main/README.md#promotion).
Argo CD syncs `kubecoder-prd` from the `prd` branch; the job only moves that branch.

!!! warning "Every promotion rolls every env pod in kubecoder-prd"
    The promoted commit changes the controller config, so prd's controller restarts every running
    environment. In-flight Claude sessions die; `work/` on ZFS survives
    ([the roll](https://github.com/pvginkel/KubeCoder/blob/main/docs/operations/deploy-operations.md#every-build-main-rolls-devs-env-pods-and-every-promotion-rolls-prds)).
    Commit and save your work in every KubeCoder environment first. No session may run this job.

## Promote

1. [ ] Save work :: every open KubeCoder session, every environment
2. [ ] Jenkins `KubeCoder/Promote-PRD`, Build with Parameters :: `commit` empty promotes the tip of
   KubeCoderDeploy `main`; a SHA on `main` promotes that commit. It rebuilds nothing: it retags
   each pinned `dev-<n>` image as `prd-<n>`, fast-forwards `prd`, and tags `release-<m>`, `<m>`
   its build number.
3. [ ] Follow it :: `track_build.py KubeCoder/Promote-PRD --buildnr <m>` from a KubeCoder
   environment (the script is DockerImages `kube-coder-dev-local-home/`), or watch the
   `kubecoder-prd` Application in Argo CD until Synced and Healthy.
4. [ ] Red at *Recording the release* :: `prd` has already moved and Argo syncs it anyway. Re-run
   with `commit` set to that SHA; the re-run records the tag alone.

## Roll back

1. [ ] `git revert` the commit on KubeCoderDeploy `main`, push :: dev follows by auto-sync
2. [ ] Promote the revert, as above :: a reverted pin commit moves all seven images back together,
   so the controller and the worker stay in agreement. The job has no rollback parameter and never
   force-moves `prd`.

!!! warning "WB-3: prd's emergency lever (D36)"
    Outside the job: force-move `prd` back to the previously promoted `release-<m-1>`. It loses
    nothing, since `main` is untouched and prd auto-syncs to it; the next promotion fast-forwards
    `prd` again. It has not been exercised, and runs on confirmation.

3. [ ] WB-3, only when a revert cannot wait :: in a KubeCoderDeploy checkout, `<m-1>` the previous
   promotion's tag

    ```
    cd <KubeCoderDeploy checkout> && git fetch -q --tags origin && git show --no-patch release-<m-1> && git push --force origin 'release-<m-1>^{commit}:refs/heads/prd'
    ```

## Background

Registry-cleanup keeps the newest 10 builds per series and the images rebuild about
weekly, so prd's pins outlive the registry after about ten weeks without a promotion, once
cleanup's dry-run is off. Promote before that.

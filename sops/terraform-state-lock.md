---
title: Terraform state lock stuck
kind: abnormal
project: Ansible
when: >-
  A Terraform run fails with "Error acquiring the state lock" and nothing is running that could
  hold it.
---

Every Terraform here reaches its state through `terraform-backend-git`: the daemon `iac-impl`
starts on srviac, the KubeCoder sidecar, wrkdev's `scripts/tf-backend.sh`, and the Argo CD
PreSync hook. The backend locks a state by pushing a branch `locks/<state path>` to
`pvginkel/TerraformState`, holding `<state path>.lock` with Terraform's lock metadata. Unlocking
deletes the branch. A run killed without a clean shutdown leaves it: an aborted Jenkins build, a
`destroy-stage` Job hit by its 30-minute deadline, a dropped `cexec`.

## Identify

| State | Who writes it | Lock branch |
|---|---|---|
| `prd/terraform.tfstate` (`terraform/prd`) | `IaC/Build-Main` and `IaC/Scheduled Drift` (plan), `IaC/Apply`, a `cexec iac terraform` in a KubeCoder environment, break-glass from wrkdev | `locks/prd/terraform.tfstate` |
| `scratch/terraform.tfstate` (`terraform/scratch`) | the same runners | `locks/scratch/terraform.tfstate` |
| `argocd/<Repo>/<stage>/terraform.tfstate` | the app's hook Job `tf-presync-<app>-<stage>` in `argocd-hooks`; `IaC/Destroy Stage` as `destroy-stage-<build#>` there | `locks/argocd/<Repo>/<stage>/terraform.tfstate` |

`<Repo>` is the deploy repo as GitHub spells it, `FieldnotesDeploy` and not `fieldnotesdeploy`.

## Steps

1. [ ] Read the lock Terraform printed: who took it, when, and for which operation.
2. [ ] Is it still alive? A running build :: `https://jenkins.webathome.org/job/IaC/`
3. [ ] A hook or destroy Job :: `kubectl -n argocd-hooks get jobs,pods`
4. [ ] Another shell :: a `cexec iac terraform` in some environment, or `tf-backend` on wrkdev
5. [ ] Alive: wait for it, or queue behind it. Nothing below.
6. [ ] List the lock branches; the stuck state's should be the only one:

    ```
    git ls-remote --heads https://github.com/pvginkel/TerraformState 'locks/*'
    ```

7. [ ] Delete that branch. That is the force-unlock:

    ```
    git push origin --delete locks/<state path>
    ```

    from a clone of TerraformState, or the branch's delete button on GitHub. Only the `locks/`
    branch; `main` holds the encrypted states.

8. [ ] Re-run what failed. A Destroy Stage build: again with the same parameters, each step skips
   what is done ([argocd § A build that stopped halfway](https://github.com/pvginkel/Ansible/blob/main/docs/runbooks/argocd.md#a-build-that-stopped-halfway)).

!!! danger "Only when nothing holds it"
    Deleting a live run's lock puts two writers on one state. Steps 2 to 4 come first, every time.

!!! note "What a clean repo looks like"
    On 2026-10-06, idle, TerraformState had only `main`. A `locks/*` branch while Jenkins and
    Argo are quiet is stale. `terraform force-unlock` has not been exercised against this
    backend; the branch delete is the documented path (AnsibleSpecs `decisions.md`,
    "Concurrency control").

!!! note "Not this"
    `IaC/*` builds waiting on each other is the `IaC Agent` node's single executor, which
    serialises the IaC jobs on purpose. A queue there is not a state lock.

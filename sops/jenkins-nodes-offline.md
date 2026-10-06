---
title: Jenkins builds stuck "All nodes of label … are offline"
kind: abnormal
project: Ansible
when: >-
  Builds queue one at a time with "All nodes of label '<job>_<n>-xxxx' are offline", although
  the Kubernetes cloud should run several agents at once.
---

The Kubernetes plugin counts agents per cloud in memory, in
`KubernetesProvisioningLimits.cloudCounts`, against the cloud's `containerCap` (3 on
2026-09-23). The count is seeded from the live `KubernetesSlave` nodes once, then kept by
`register` on each pod request and `unregister` when a node is deleted. An agent that goes away
without `unregister` keeps its slot forever. On 2026-09-23 two slots leaked, most likely across a
controller restart: an adopted agent was removed by the Reaper instead of terminated. With the cap
reached on paper, nothing new is provisioned, the controller log shows `Created Pod` strictly one
at a time, and every build waits for a pod to end. The operator has seen it more than once.

No template has an `instanceCap` and there is no ResourceQuota, so a serial queue under the cap
is this.

## Steps

1. [ ] Count the agents actually alive on the Nodes page against the cap. All three busy is not a
   leak.
2. [ ] In the Script Console (Manage Jenkins → Script Console), compare the plugin's count with the
   live agents:

    ```groovy
    import jenkins.model.Jenkins
    import org.csanchez.jenkins.plugins.kubernetes.KubernetesProvisioningLimits
    import org.csanchez.jenkins.plugins.kubernetes.KubernetesSlave

    def counts = KubernetesProvisioningLimits.get().@cloudCounts
    def live = Jenkins.get().nodes.findAll { it instanceof KubernetesSlave }
    println "plugin's cloudCounts: ${counts}"
    println "live KubernetesSlave executors: " +
        live.groupBy { it.cloudName }.collectEntries { c, ns -> [(c): ns.sum { it.numExecutors } ?: 0] }
    ```

3. [ ] Take several samples. The count goes up when a pod is requested, before its node exists, so
   one sample of count > live while a build is provisioning is not a leak. A count that stays above
   the live sum while nothing is provisioning is.
4. [ ] Reset the count to the live sum, under the cloud name step 2 printed (`Kubernetes` on
   2026-09-23). It takes effect at once, no restart:

    ```groovy
    KubernetesProvisioningLimits.get().@cloudCounts.put('Kubernetes', <live sum>)
    ```

5. [ ] The queue drains on its own. Watch the next few builds start in parallel.

!!! warning "Not yet run as written"
    The snippets are grounded in the plugin's source (`KubernetesProvisioningLimits.java`:
    `get()`, the private `cloudCounts` map keyed by `cloud.name`, `KubernetesSlave.getCloudName()`)
    and reflect a private field. The 2026-09-23 fix was an equivalent script sent through
    `/scriptText` as admin. These exact lines have not been run.

!!! note "Not this"
    `IaC/*` jobs queueing behind one another is the `IaC Agent` node's single executor, by design.

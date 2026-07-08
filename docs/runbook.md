# Chaos Experiment Runbook

This runbook describes how to run chaos experiments **safely** in a controlled
environment. Chaos engineering is only valuable when it is deliberate: define a
hypothesis, contain the blast radius, and always have an abort plan.

## Principles

1. **Start in dev/staging.** Never run a new experiment in production first.
2. **Define a steady-state hypothesis** before injecting a fault. If you cannot
   measure "healthy", you cannot measure "broken".
3. **Minimize blast radius.** Target a single deployment, a fraction of pods,
   and a bounded duration.
4. **Observe.** Watch dashboards and alerts for the whole experiment window.
5. **Have an abort button.** Know the exact command to stop the experiment.

## Pre-flight checklist

- [ ] Target namespace is `chaos-testing` (or an approved non-prod namespace).
- [ ] The runner ServiceAccount and RBAC are installed (`kubernetes/`).
- [ ] Prometheus is reachable at `PROMETHEUS_URL`.
- [ ] Steady-state hypotheses hold **before** starting (`chaos-lab run … --dry-run`).
- [ ] On-call / owning team is aware of the game day window.

## Running an experiment

List available experiments and their hypotheses:

```bash
chaos-lab list
```

Preview an experiment without touching the cluster (evaluates steady state only):

```bash
chaos-lab run pod-kill --engine chaos-mesh --dry-run
```

Run for real. The runner evaluates steady state, applies the manifest, waits for
the configured duration, tears the experiment down, then re-checks steady state:

```bash
chaos-lab run pod-kill --engine chaos-mesh
```

You can also apply a manifest directly with `kubectl`:

```bash
kubectl apply -n chaos-testing -f experiments/chaos-mesh/pod-kill.yaml
```

## Blast radius controls

| Control          | Chaos Mesh field         | Litmus env                 |
| ---------------- | ------------------------ | -------------------------- |
| Pod fraction     | `mode` / `value`         | `PODS_AFFECTED_PERC`       |
| Duration         | `spec.duration`          | `TOTAL_CHAOS_DURATION`     |
| Target selector  | `selector.labelSelectors`| `appinfo.applabel`         |
| Namespace        | `selector.namespaces`    | `appinfo.appns`            |

Keep `mode: one` (Chaos Mesh) or a low `PODS_AFFECTED_PERC` (Litmus) for the
first run of any experiment.

## Aborting

Chaos Mesh — delete the chaos resource; faults are reverted automatically:

```bash
kubectl delete -n chaos-testing -f experiments/chaos-mesh/network-delay.yaml
```

Litmus — set the engine state to `stop`:

```bash
kubectl patch chaosengine pod-delete -n chaos-testing \
  --type merge -p '{"spec":{"engineState":"stop"}}'
```

The `ExperimentRunner` also aborts automatically if the steady-state hypothesis
does **not** hold before the fault is injected.

## After the experiment

- Confirm the system returned to steady state (the runner reports this).
- Record findings and any follow-up actions.
- File issues for weaknesses discovered (use the bug report template).

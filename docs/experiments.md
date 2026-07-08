# Experiment Catalog

Every experiment ships as a manifest under `experiments/<engine>/` and carries
its metadata (duration, description, steady-state hypotheses) in
`chaos-lab.dev/*` annotations so the runner and `chaos-lab list` stay in sync.

## LitmusChaos (`experiments/litmus/`)

| Experiment        | Kind (+ ChaosExperiment)      | Duration | Steady-state hypothesis                                   |
| ----------------- | ----------------------------- | -------- | -------------------------------------------------------- |
| `pod-delete`      | ChaosEngine → `pod-delete`    | 60s      | `avg(up) >= 0.99` and `>= 2` available replicas          |
| `node-cpu-hog`    | ChaosEngine → `node-cpu-hog`  | 120s     | p99 request latency `< 0.5s`                             |
| `network-latency` | ChaosEngine → `pod-network-latency` | 90s | 5xx error rate `< 5%`                                    |

## Chaos Mesh (`experiments/chaos-mesh/`)

| Experiment      | Kind          | Duration | Steady-state hypothesis                              |
| --------------- | ------------- | -------- | --------------------------------------------------- |
| `pod-kill`      | PodChaos      | 30s      | `avg(up) >= 0.99` and `>= 2` available replicas     |
| `network-delay` | NetworkChaos  | 90s      | 5xx error rate `< 5%`                               |
| `stress-cpu`    | StressChaos   | 120s     | p99 request latency `< 0.5s`                        |
| `io-fault`      | IOChaos       | 60s      | 2xx success rate `>= 95%`                           |

## Hypothesis format

Hypotheses are evaluated against Prometheus. Each declares a PromQL `metric`, a
`comparator` (`lt`, `le`, `gt`, `ge`, `eq`, `ne`), and a numeric `threshold`:

```yaml
chaos-lab.dev/steady-state: |
  - name: availability
    metric: 'avg(up{job="target-app"})'
    comparator: ge
    threshold: 0.99
```

The runner checks all hypotheses **before** injecting the fault (aborting if they
do not hold) and again **after** teardown to confirm the system recovered.

## Adding a new experiment

1. Drop a valid manifest into `experiments/litmus/` or `experiments/chaos-mesh/`.
2. Add the `chaos-lab.dev/description`, `chaos-lab.dev/duration-seconds`, and
   `chaos-lab.dev/steady-state` annotations.
3. Run `chaos-lab validate` and `chaos-lab list` to confirm discovery.

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-08

### Added

- `chaos-lab` CLI with `list`, `validate`, and `run` subcommands.
- Typed experiment runner (`chaos_lab.runner`) that evaluates steady-state
  hypotheses before and after each experiment and produces structured results.
- Steady-state evaluation against Prometheus (`chaos_lab.steady_state`).
- Experiment catalog loader reading `chaos-lab.dev/*` annotations.
- LitmusChaos experiments: pod-delete, node-cpu-hog, network-latency.
- Chaos Mesh experiments: pod-kill, network-delay, stress-cpu, io-fault.
- Kubernetes RBAC (ServiceAccount, Role, RoleBinding) and a scheduled runner
  CronJob.
- Terraform module to install Litmus or Chaos Mesh via Helm, with dev/prod
  environments.
- Documentation: README, experiment catalog, safety runbook, architecture.
- CI pipeline, pre-commit hooks, and open-source project files.

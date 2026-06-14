"""
Chaos Engineering Lab - CLI for running controlled chaos experiments on Kubernetes.

Experiments:
  - pod-kill: randomly kill pods in a namespace
  - network-delay: introduce latency via tc (requires privileged pod)
  - cpu-stress: stress CPU on target pods
  - memory-stress: stress memory on target pods
  - node-drain: cordon and drain a node

Usage:
    python chaos_runner.py pod-kill --namespace default --label-selector app=nginx
    python chaos_runner.py network-delay --namespace default --label-selector app=api --delay 200ms
    python chaos_runner.py cpu-stress --namespace default --label-selector app=worker --duration 60
"""
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import click
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger("chaos-runner")


def _kubectl(args: list, capture: bool = True) -> tuple[int, str, str]:
    cmd = ["kubectl"] + args
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True, timeout=120)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return 1, "", "kubectl not found. Install from https://kubernetes.io/docs/tasks/tools/"
    except subprocess.TimeoutExpired:
        return 1, "", "kubectl command timed out"


def _get_pods(namespace: str, label_selector: Optional[str] = None) -> list[str]:
    args = ["get", "pods", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"]
    if label_selector:
        args += ["-l", label_selector]
    rc, stdout, stderr = _kubectl(args)
    if rc != 0:
        raise click.ClickException(f"Failed to list pods: {stderr}")
    pods = stdout.strip().split() if stdout.strip() else []
    return pods


def _log_experiment(experiment: str, target: str, result: str, details: dict = None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": experiment,
        "target": target,
        "result": result,
        "details": details or {},
    }
    log_file = os.environ.get("CHAOS_LOG_FILE", "chaos-experiments.json")
    try:
        existing = []
        if os.path.exists(log_file):
            with open(log_file) as f:
                existing = json.load(f)
        existing.append(entry)
        with open(log_file, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        logger.warning("Could not write experiment log: %s", e)
    logger.info("Experiment logged: %s -> %s [%s]", experiment, target, result)


@click.group()
@click.version_option("1.0.0", prog_name="chaos-runner")
def cli():
    """Chaos Engineering Lab — run controlled chaos experiments on Kubernetes."""


@cli.command("pod-kill")
@click.option("--namespace", "-n", default="default", show_default=True)
@click.option("--label-selector", "-l", default=None, help="Label selector e.g. app=nginx")
@click.option("--count", default=1, show_default=True, type=int, help="Number of pods to kill")
@click.option("--dry-run", is_flag=True, help="Show what would be killed without doing it")
@click.option("--confirm/--no-confirm", default=True, help="Ask for confirmation before killing")
def pod_kill(namespace: str, label_selector: Optional[str], count: int, dry_run: bool, confirm: bool):
    """Kill random pods in a namespace to test resilience.

    \b
    Example:
        python chaos_runner.py pod-kill --namespace default --label-selector app=nginx --count 2
    """
    pods = _get_pods(namespace, label_selector)
    if not pods:
        click.echo(f"No pods found in namespace '{namespace}'" + (f" with selector '{label_selector}'" if label_selector else ""))
        return

    victims = random.sample(pods, min(count, len(pods)))

    click.echo(f"\n🎯 Chaos Experiment: Pod Kill")
    click.echo(f"   Namespace: {namespace}")
    click.echo(f"   Target pods: {', '.join(victims)}")

    if dry_run:
        click.echo(click.style("   [DRY RUN] No pods were killed.", fg="yellow"))
        return

    if confirm:
        click.confirm(f"\nKill {len(victims)} pod(s)?", abort=True)

    killed = []
    for pod in victims:
        rc, stdout, stderr = _kubectl(["delete", "pod", pod, "-n", namespace, "--grace-period=0", "--force"])
        if rc == 0:
            killed.append(pod)
            click.echo(click.style(f"  ✓ Killed pod: {pod}", fg="green"))
        else:
            click.echo(click.style(f"  ✗ Failed to kill pod {pod}: {stderr}", fg="red"))

    _log_experiment("pod-kill", namespace, "completed", {"killed": killed, "label_selector": label_selector})
    click.echo(click.style(f"\n✓ Killed {len(killed)}/{len(victims)} pods.", fg="green"))


@cli.command("network-delay")
@click.option("--namespace", "-n", default="default", show_default=True)
@click.option("--label-selector", "-l", required=True, help="Target pods label selector")
@click.option("--delay", default="200ms", show_default=True, help="Network delay (e.g. 200ms, 1s)")
@click.option("--duration", default=60, show_default=True, type=int, help="Duration in seconds")
@click.option("--dry-run", is_flag=True)
def network_delay(namespace: str, label_selector: str, delay: str, duration: int, dry_run: bool):
    """Inject network latency into pods using tc (traffic control).

    \b
    Example:
        python chaos_runner.py network-delay --namespace default --label-selector app=api --delay 500ms --duration 30
    """
    pods = _get_pods(namespace, label_selector)
    if not pods:
        raise click.ClickException(f"No pods found with selector '{label_selector}' in namespace '{namespace}'")

    click.echo(f"\n🌐 Chaos Experiment: Network Delay")
    click.echo(f"   Pods: {', '.join(pods)}")
    click.echo(f"   Delay: {delay} for {duration}s")

    if dry_run:
        click.echo(click.style("   [DRY RUN] No changes applied.", fg="yellow"))
        return

    for pod in pods:
        inject_cmd = f"tc qdisc add dev eth0 root netem delay {delay}"
        clean_cmd = "tc qdisc del dev eth0 root netem"
        rc, out, err = _kubectl(["exec", pod, "-n", namespace, "--", "sh", "-c", inject_cmd])
        if rc == 0:
            click.echo(click.style(f"  ✓ Injected {delay} delay into {pod}", fg="green"))
        else:
            click.echo(click.style(f"  ⚠ Could not inject delay into {pod} (may need privileged mode): {err}", fg="yellow"))

    if duration > 0:
        click.echo(f"  Waiting {duration}s before cleanup...")
        time.sleep(duration)
        for pod in pods:
            clean_cmd = "tc qdisc del dev eth0 root netem"
            _kubectl(["exec", pod, "-n", namespace, "--", "sh", "-c", clean_cmd])
        click.echo(click.style("  ✓ Network delay removed.", fg="green"))

    _log_experiment("network-delay", namespace, "completed", {"delay": delay, "duration": duration, "pods": pods})


@cli.command("cpu-stress")
@click.option("--namespace", "-n", default="default", show_default=True)
@click.option("--label-selector", "-l", required=True)
@click.option("--duration", default=60, show_default=True, type=int, help="Duration in seconds")
@click.option("--workers", default=2, show_default=True, type=int, help="Number of stress workers")
@click.option("--dry-run", is_flag=True)
def cpu_stress(namespace: str, label_selector: str, duration: int, workers: int, dry_run: bool):
    """Stress CPU on target pods to test autoscaling and resource limits.

    \b
    Example:
        python chaos_runner.py cpu-stress --namespace default --label-selector app=worker --duration 60
    """
    pods = _get_pods(namespace, label_selector)
    if not pods:
        raise click.ClickException(f"No pods found with selector '{label_selector}'")

    click.echo(f"\n💻 Chaos Experiment: CPU Stress")
    click.echo(f"   Pods: {', '.join(pods)}")
    click.echo(f"   Workers: {workers}, Duration: {duration}s")

    if dry_run:
        click.echo(click.style("   [DRY RUN] No stress applied.", fg="yellow"))
        return

    for pod in pods:
        stress_cmd = f"stress-ng --cpu {workers} --timeout {duration}s --metrics-brief &"
        rc, out, err = _kubectl(["exec", pod, "-n", namespace, "--", "sh", "-c", stress_cmd])
        if rc == 0:
            click.echo(click.style(f"  ✓ CPU stress started on {pod}", fg="green"))
        else:
            # fallback: python-based CPU stress
            fallback = f"python3 -c 'import time; [sum(i*i for i in range(10000)) for _ in range({duration})]' &"
            rc2, _, _ = _kubectl(["exec", pod, "-n", namespace, "--", "sh", "-c", fallback])
            status = "✓" if rc2 == 0 else "⚠"
            click.echo(click.style(f"  {status} CPU stress (fallback) on {pod}", fg="green" if rc2 == 0 else "yellow"))

    _log_experiment("cpu-stress", namespace, "initiated", {"workers": workers, "duration": duration, "pods": pods})
    click.echo(click.style(f"\n✓ CPU stress initiated on {len(pods)} pod(s) for {duration}s.", fg="green"))


@cli.command("list-experiments")
@click.option("--log-file", default="chaos-experiments.json", show_default=True)
def list_experiments(log_file: str):
    """Show history of chaos experiments run.

    \b
    Example:
        python chaos_runner.py list-experiments
    """
    if not os.path.exists(log_file):
        click.echo("No experiments recorded yet.")
        return

    with open(log_file) as f:
        experiments = json.load(f)

    click.echo(f"\n📋 Chaos Experiment History ({len(experiments)} runs)\n")
    for exp in experiments[-20:]:  # last 20
        click.echo(f"  [{exp['timestamp']}] {exp['experiment']} -> {exp['target']} [{exp['result']}]")


@cli.command("node-drain")
@click.option("--node", "-n", required=True, help="Node name to drain")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def node_drain(node: str, dry_run: bool, yes: bool):
    """Cordon and drain a Kubernetes node to test pod rescheduling.

    \b
    Example:
        python chaos_runner.py node-drain --node worker-1 --dry-run
    """
    click.echo(f"\n🖥️  Chaos Experiment: Node Drain")
    click.echo(f"   Node: {node}")

    if dry_run:
        rc, out, _ = _kubectl(["drain", node, "--dry-run=client", "--ignore-daemonsets", "--delete-emptydir-data"])
        click.echo(out)
        click.echo(click.style("   [DRY RUN] No drain applied.", fg="yellow"))
        return

    if not yes:
        click.confirm(f"\nDrain node '{node}'? This will evict all pods.", abort=True)

    rc, out, err = _kubectl(["cordon", node])
    if rc != 0:
        raise click.ClickException(f"Failed to cordon node: {err}")
    click.echo(click.style(f"  ✓ Node '{node}' cordoned.", fg="green"))

    rc, out, err = _kubectl(["drain", node, "--ignore-daemonsets", "--delete-emptydir-data", "--grace-period=30"])
    if rc == 0:
        click.echo(click.style(f"  ✓ Node '{node}' drained.", fg="green"))
    else:
        click.echo(click.style(f"  ⚠ Drain partially failed: {err}", fg="yellow"))

    _log_experiment("node-drain", node, "completed" if rc == 0 else "partial")


if __name__ == "__main__":
    cli()
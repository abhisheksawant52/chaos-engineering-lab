output "namespace" {
  description = "Namespace the chaos platform was installed into."
  value       = kubernetes_namespace.chaos.metadata[0].name
}

output "engine" {
  description = "Chaos platform that was installed."
  value       = var.engine
}

output "release_name" {
  description = "Name of the installed Helm release."
  value       = var.engine == "chaos-mesh" ? "chaos-mesh" : "litmus"
}

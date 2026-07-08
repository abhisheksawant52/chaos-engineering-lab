output "namespace" {
  description = "Namespace the chaos platform was installed into."
  value       = module.chaos_platform.namespace
}

output "engine" {
  description = "Chaos platform that was installed."
  value       = module.chaos_platform.engine
}

output "release_name" {
  description = "Name of the installed Helm release."
  value       = module.chaos_platform.release_name
}

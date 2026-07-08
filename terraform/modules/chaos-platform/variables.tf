variable "namespace" {
  description = "Namespace to install the chaos platform into."
  type        = string
  default     = "chaos-testing"
}

variable "engine" {
  description = "Which chaos platform to install: 'litmus' or 'chaos-mesh'."
  type        = string
  default     = "chaos-mesh"

  validation {
    condition     = contains(["litmus", "chaos-mesh"], var.engine)
    error_message = "engine must be either 'litmus' or 'chaos-mesh'."
  }
}

variable "chart_version" {
  description = "Helm chart version to install."
  type        = string
  default     = "2.6.3"
}

variable "enable_dashboard" {
  description = "Whether to deploy the platform web dashboard."
  type        = bool
  default     = true
}

variable "container_runtime" {
  description = "Container runtime on the nodes (containerd, crio, docker)."
  type        = string
  default     = "containerd"
}

variable "container_socket_path" {
  description = "Path to the container runtime socket on the nodes."
  type        = string
  default     = "/run/containerd/containerd.sock"
}

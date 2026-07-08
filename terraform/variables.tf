variable "kubeconfig" {
  description = "Path to the kubeconfig file used to reach the cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context to use."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace to install the chaos platform into."
  type        = string
  default     = "chaos-testing"
}

variable "engine" {
  description = "Which chaos platform to install: 'litmus' or 'chaos-mesh'."
  type        = string
  default     = "chaos-mesh"
}

variable "chart_version" {
  description = "Helm chart version for the selected engine."
  type        = string
  default     = "2.6.3"
}

variable "enable_dashboard" {
  description = "Whether to deploy the platform web dashboard."
  type        = bool
  default     = true
}

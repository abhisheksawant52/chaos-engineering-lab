# Installs a chaos engineering platform (LitmusChaos or Chaos Mesh) into a
# dedicated namespace via Helm.

resource "kubernetes_namespace" "chaos" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name"       = "chaos-engineering-lab"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "helm_release" "chaos_mesh" {
  count = var.engine == "chaos-mesh" ? 1 : 0

  name       = "chaos-mesh"
  repository = "https://charts.chaos-mesh.org"
  chart      = "chaos-mesh"
  version    = var.chart_version
  namespace  = kubernetes_namespace.chaos.metadata[0].name

  set {
    name  = "dashboard.create"
    value = tostring(var.enable_dashboard)
  }

  set {
    name  = "chaosDaemon.runtime"
    value = var.container_runtime
  }

  set {
    name  = "chaosDaemon.socketPath"
    value = var.container_socket_path
  }
}

resource "helm_release" "litmus" {
  count = var.engine == "litmus" ? 1 : 0

  name             = "litmus"
  repository       = "https://litmuschaos.github.io/litmus-helm/"
  chart            = "litmus"
  version          = var.chart_version
  namespace        = kubernetes_namespace.chaos.metadata[0].name
  create_namespace = false

  set {
    name  = "portal.frontend.service.type"
    value = "ClusterIP"
  }
}

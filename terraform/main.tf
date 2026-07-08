# Root module: install the chaos platform on the target cluster.

module "chaos_platform" {
  source = "./modules/chaos-platform"

  namespace        = var.namespace
  engine           = var.engine
  chart_version    = var.chart_version
  enable_dashboard = var.enable_dashboard
}

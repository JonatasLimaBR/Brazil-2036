variable "project_id" {
  type        = string
  description = "GCP dev project id (created by scripts/bootstrap.sh)."
}

variable "region" {
  type        = string
  description = "Default region for regional resources."
  default     = "southamerica-east1"
}

variable "github_repo" {
  type        = string
  description = "owner/name of the GitHub repository allowed to deploy."
}

variable "budget_amount_brl" {
  type        = number
  description = "Monthly budget amount (BRL) for the dev project alert. 1800, not 50 (ADR-062): AlloyDB's smallest viable cluster costs ~US$300/month continuously."
  default     = 1800
}

variable "billing_account" {
  type        = string
  description = "Billing account id, required only for the budget resource."
  default     = ""
}

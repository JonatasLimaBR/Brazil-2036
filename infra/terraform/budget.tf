resource "google_billing_budget" "dev" {
  count = var.billing_account == "" ? 0 : 1

  billing_account = var.billing_account
  display_name    = "brasil2036-dev monthly guardrail"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "BRL"
      units         = tostring(var.budget_amount_brl)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}

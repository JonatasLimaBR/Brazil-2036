#!/usr/bin/env bash
# One-time GCP bootstrap. Run by a human with Billing Account Admin.
# Creates only what Workload Identity Federation cannot create for itself:
#   project + billing link + base APIs + Terraform state bucket
#   + WIF pool/provider + the deployer service account CI impersonates.
# Everything else is managed by Terraform running in GitHub Actions.
#
# Usage:
#   PROJECT_ID=brasil2036-dev REGION=southamerica-east1 \
#   BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX GITHUB_REPO=JonatasLimaBR/Brazil-2036 \
#   bash scripts/bootstrap.sh
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:?set REGION}"
: "${BILLING_ACCOUNT:?set BILLING_ACCOUNT}"
: "${GITHUB_REPO:?set GITHUB_REPO (owner/name)}"

STATE_BUCKET="${PROJECT_ID}-tfstate"
POOL_ID="github-pool"
PROVIDER_ID="github-provider"
DEPLOYER_SA="tf-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

echo "== project"
gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud projects create "$PROJECT_ID"
gcloud billing projects link "$PROJECT_ID" --billing-account "$BILLING_ACCOUNT"
gcloud config set project "$PROJECT_ID"

echo "== base APIs"
gcloud services enable \
  cloudresourcemanager.googleapis.com serviceusage.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  storage.googleapis.com

echo "== terraform state bucket"
gcloud storage buckets describe "gs://${STATE_BUCKET}" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://${STATE_BUCKET}" \
    --location "$REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning

echo "== deployer service account"
gcloud iam service-accounts describe "$DEPLOYER_SA" >/dev/null 2>&1 || \
  gcloud iam service-accounts create tf-deployer \
    --display-name "Terraform deployer (GitHub Actions via WIF)"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
for role in \
  roles/serviceusage.serviceUsageAdmin \
  roles/storage.admin \
  roles/bigquery.admin \
  roles/artifactregistry.admin \
  roles/run.admin \
  roles/iam.serviceAccountAdmin \
  roles/resourcemanager.projectIamAdmin \
  roles/billing.projectManager \
  roles/serviceaccount.user ; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${DEPLOYER_SA}" --role "$role" --condition=None >/dev/null
done

echo "== workload identity federation"
gcloud iam workload-identity-pools describe "$POOL_ID" --location=global >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
  --location=global --workload-identity-pool="$POOL_ID" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --location=global --workload-identity-pool="$POOL_ID" \
    --display-name="GitHub OIDC" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

POOL_NAME="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}" >/dev/null

PROVIDER_RESOURCE="${POOL_NAME}/providers/${PROVIDER_ID}"

cat <<EOF

== done. Add these as GitHub repo Actions *variables*
   (Settings -> Secrets and variables -> Actions -> Variables):

   GCP_PROJECT          = ${PROJECT_ID}
   GCP_REGION           = ${REGION}
   GCP_TF_STATE_BUCKET  = ${STATE_BUCKET}
   GCP_WIF_PROVIDER     = ${PROVIDER_RESOURCE}
   GCP_DEPLOYER_SA      = ${DEPLOYER_SA}

Then push to main (or run the "infra" workflow) and Terraform provisions the rest.
EOF

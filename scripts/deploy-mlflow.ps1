param(
    # GCP project id where all MLflow resources will be created.
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    # GCP region used by Cloud Run, Cloud SQL, Artifact Registry, and Storage.
    [string] $Region = "us-central1",

    # Terraform stack that defines the MLflow infrastructure.
    [string] $TfDir = "infra\terraform\mlflow",

    # Folder containing the MLflow Dockerfile used by Cloud Build.
    [string] $ImageSourceDir = "deploy\mlflow-cloud-run",

    # Passes -auto-approve to Terraform for non-interactive deploys.
    [switch] $AutoApprove
)

# Stop PowerShell errors immediately instead of continuing with a broken deploy.
$ErrorActionPreference = "Stop"

# In PowerShell 7+, make native commands like gcloud/terraform respect
# $ErrorActionPreference. Windows PowerShell 5.1 ignores this setting, so the
# Invoke-Checked helper below still checks exit codes explicitly.
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $true
}

# Runs a CLI command and fails the script if the command exits unsuccessfully.
# This prevents false success messages after a failed terraform or gcloud step.
function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Command,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]] $Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

# Resolve paths from the script location so the script works from any shell
# working directory, as long as it is run from this repository.
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$terraformDir = Resolve-Path (Join-Path $repoRoot $TfDir)
$imageDir = Resolve-Path (Join-Path $repoRoot $ImageSourceDir)
$tfvarsPath = Join-Path $terraformDir "terraform.tfvars"

# terraform.tfvars is intentionally not committed because it contains local
# project settings. If missing, create it from the example and ask the user to
# fill it in before continuing.
if (-not (Test-Path $tfvarsPath)) {
    Copy-Item (Join-Path $terraformDir "terraform.tfvars.example") $tfvarsPath
    Write-Host "Created $tfvarsPath. Edit project_id/settings there, then rerun this script."
    exit 1
}

# Keep Terraform interactive by default. Use -AutoApprove only when you want the
# script to apply changes without a confirmation prompt.
$approvalArgs = @()
if ($AutoApprove) {
    $approvalArgs += "-auto-approve"
}

# Run Terraform commands from the stack directory so relative paths, lock files,
# and local state stay in one predictable place.
Push-Location $terraformDir
try {
    # Point gcloud at the selected project. Terraform also receives this value
    # through -var so both tools operate on the same GCP project.
    Invoke-Checked gcloud config set project $ProjectId

    # Download Terraform providers and prepare the local working directory.
    Invoke-Checked terraform init

    # First Terraform pass:
    # Create foundational resources before the container image exists:
    # - required GCP APIs
    # - Artifact Registry repository
    # - Cloud Storage artifact bucket
    # - Cloud SQL database
    # - service account, secrets, and IAM
    # Cloud Run is intentionally skipped here with deploy_cloud_run=false because
    # it needs the Docker image URI after the image is built and pushed.
    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_cloud_run=false"

    # Read the canonical image URI from Terraform output so the image tag always
    # matches the Artifact Registry repository Terraform created.
    $image = (& terraform output -raw mlflow_image_uri)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    # Build the MLflow tracking-server container from deploy/mlflow-cloud-run and
    # push it to Artifact Registry using Google Cloud Build.
    Invoke-Checked gcloud builds submit $imageDir --tag $image

    # Second Terraform pass:
    # Now that the image exists, create or update the Cloud Run service with:
    # - the MLflow image
    # - Cloud SQL socket mount
    # - durable artifact bucket env var
    # - backend database connection env var
    # - public/private access settings from terraform.tfvars
    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_cloud_run=true" `
        -var="container_image=$image"

    # Print the final MLflow URL and the exact environment variable the ML team
    # should use before running training jobs.
    $serviceUrl = (& terraform output -raw cloud_run_service_url)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }
    Write-Host ""
    Write-Host "MLflow is deployed."
    Write-Host "Tracking URI: $serviceUrl"
    Write-Host "Use this in training: `$env:MLFLOW_TRACKING_URI='$serviceUrl'"
}
finally {
    # Always return to the caller's original directory, even if a deploy step
    # fails halfway through.
    Pop-Location
}

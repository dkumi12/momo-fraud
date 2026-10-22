param(
    # GCP project id where the prediction API will be deployed.
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    # GCP region used by Cloud Run and Artifact Registry.
    [string] $Region = "us-central1",

    # Terraform stack that defines the prediction API infrastructure.
    [string] $TfDir = "infra\terraform\prediction-api",

    # Docker build context. Use the repo root because the API image needs app.py,
    # features.py, templates/, requirements.txt, and models/.
    [string] $ImageSourceDir = ".",

    # Dockerfile path relative to the build context.
    [string] $Dockerfile = "deploy\prediction-api\Dockerfile",

    # Cloud Build config that builds the API image using the Dockerfile above.
    [string] $CloudBuildConfig = "deploy\prediction-api\cloudbuild.yaml",

    # Passes -auto-approve to Terraform for non-interactive deploys.
    [switch] $AutoApprove
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $true
}

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

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$terraformDir = Resolve-Path (Join-Path $repoRoot $TfDir)
$imageDir = Resolve-Path (Join-Path $repoRoot $ImageSourceDir)
$tfvarsPath = Join-Path $terraformDir "terraform.tfvars"
$dockerfilePath = Join-Path $repoRoot $Dockerfile
$cloudBuildConfigPath = Join-Path $repoRoot $CloudBuildConfig

if (-not (Test-Path $tfvarsPath)) {
    Copy-Item (Join-Path $terraformDir "terraform.tfvars.example") $tfvarsPath
    Write-Host "Created $tfvarsPath. Edit project_id/settings there, then rerun this script."
    exit 1
}

if (-not (Test-Path $dockerfilePath)) {
    throw "Missing API Dockerfile: $Dockerfile"
}

if (-not (Test-Path $cloudBuildConfigPath)) {
    throw "Missing Cloud Build config: $CloudBuildConfig"
}

$requiredPaths = @("app.py", "features.py", "requirements.txt", "templates", "models")
foreach ($path in $requiredPaths) {
    $fullPath = Join-Path $repoRoot $path
    if (-not (Test-Path $fullPath)) {
        throw "Missing required API build input: $path. Merge/copy dwilson's API files and generate model artifacts first."
    }
}

$requiredModelArtifacts = @(
    "models\xgboost.pkl",
    "models\caps.json",
    "models\feature_columns.json",
    "models\threshold.json"
)
foreach ($path in $requiredModelArtifacts) {
    $fullPath = Join-Path $repoRoot $path
    if (-not (Test-Path $fullPath)) {
        throw "Missing model artifact: $path. Run the training pipeline before deploying the API."
    }
}

$approvalArgs = @()
if ($AutoApprove) {
    $approvalArgs += "-auto-approve"
}

Push-Location $terraformDir
try {
    Invoke-Checked gcloud config set project $ProjectId

    Invoke-Checked terraform init

    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_cloud_run=false"

    $image = (& terraform output -raw prediction_api_image_uri)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    Invoke-Checked gcloud builds submit $imageDir --config $cloudBuildConfigPath --substitutions "_IMAGE=$image"

    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_cloud_run=true" `
        -var="container_image=$image"

    $serviceUrl = (& terraform output -raw prediction_api_service_url)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Prediction API is deployed."
    Write-Host "Service URL: $serviceUrl"
    Write-Host "Health check: $serviceUrl/health"
}
finally {
    Pop-Location
}

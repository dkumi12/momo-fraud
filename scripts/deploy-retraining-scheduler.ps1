param(
    # GCP project id where retraining automation will be deployed.
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    # GCP region used by Cloud Run Jobs, Scheduler, and Artifact Registry.
    [string] $Region = "us-central1",

    # Terraform stack that defines the retraining scheduler infrastructure.
    [string] $TfDir = "infra\terraform\retraining-scheduler",

    # Docker build context. Use repo root because the training image needs
    # train.py, features.py, and requirements.txt.
    [string] $ImageSourceDir = ".",

    # Local CSV to upload into the Terraform-managed training data bucket.
    [string] $TrainingDataFile = "Pay-sim.csv",

    # Cloud Build config that builds the retraining image.
    [string] $CloudBuildConfig = "deploy\training-job\cloudbuild.yaml",

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
$cloudBuildConfigPath = Join-Path $repoRoot $CloudBuildConfig

if (-not (Test-Path $tfvarsPath)) {
    Copy-Item (Join-Path $terraformDir "terraform.tfvars.example") $tfvarsPath
    Write-Host "Created $tfvarsPath. Edit project_id/settings there, then rerun this script."
    exit 1
}

if (-not (Test-Path $cloudBuildConfigPath)) {
    throw "Missing Cloud Build config: $CloudBuildConfig"
}

$requiredPaths = @("train.py", "features.py", "requirements.txt", $TrainingDataFile)
foreach ($path in $requiredPaths) {
    $fullPath = Join-Path $repoRoot $path
    if (-not (Test-Path $fullPath)) {
        throw "Missing required retraining input: $path"
    }
}

$trainingDataPath = Resolve-Path (Join-Path $repoRoot $TrainingDataFile)

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
        -var="deploy_job=false"

    $image = (& terraform output -raw retraining_image_uri)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    $trainingDataUri = (& terraform output -raw training_data_uri)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    Write-Host "Uploading latest training data to $trainingDataUri"
    Invoke-Checked gcloud storage cp $trainingDataPath $trainingDataUri

    Invoke-Checked gcloud builds submit $imageDir --config $cloudBuildConfigPath --substitutions "_IMAGE=$image"

    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_job=true" `
        -var="container_image=$image"

    $manualRun = (& terraform output -raw manual_run_command)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Retraining scheduler is deployed."
    Write-Host "Manual test command: $manualRun"
}
finally {
    Pop-Location
}

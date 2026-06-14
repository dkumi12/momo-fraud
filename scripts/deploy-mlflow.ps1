param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    [string] $Region = "us-central1",
    [string] $TfDir = "infra\terraform\mlflow",
    [string] $ImageSourceDir = "deploy\mlflow-cloud-run",
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

if (-not (Test-Path $tfvarsPath)) {
    Copy-Item (Join-Path $terraformDir "terraform.tfvars.example") $tfvarsPath
    Write-Host "Created $tfvarsPath. Edit project_id/settings there, then rerun this script."
    exit 1
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

    $image = (& terraform output -raw mlflow_image_uri)
    if ($LASTEXITCODE -ne 0) {
        throw "terraform output failed with exit code $LASTEXITCODE"
    }

    Invoke-Checked gcloud builds submit $imageDir --tag $image

    Invoke-Checked terraform apply @approvalArgs `
        -var-file="terraform.tfvars" `
        -var="project_id=$ProjectId" `
        -var="region=$Region" `
        -var="deploy_cloud_run=true" `
        -var="container_image=$image"

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
    Pop-Location
}

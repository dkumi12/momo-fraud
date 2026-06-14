param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    [string] $Region = "us-central1",
    [string] $ServiceName = "momo-mlflow",
    [string] $ArtifactRepo = "momo-fraud",

    [Parameter(Mandatory = $true)]
    [string] $Bucket,

    [Parameter(Mandatory = $true)]
    [string] $BackendStoreUri,

    [string] $CloudSqlInstance = "",
    [switch] $AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

gcloud config set project $ProjectId

gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com `
    sqladmin.googleapis.com `
    storage.googleapis.com

$repoExists = gcloud artifacts repositories describe $ArtifactRepo --location $Region 2>$null
if (-not $repoExists) {
    gcloud artifacts repositories create $ArtifactRepo `
        --repository-format=docker `
        --location=$Region
}

$image = "$Region-docker.pkg.dev/$ProjectId/$ArtifactRepo/mlflow-tracking:latest"
gcloud builds submit "$PSScriptRoot" --tag $image

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }
$envVars = "ARTIFACT_ROOT=$Bucket,BACKEND_STORE_URI=$BackendStoreUri"

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $image,
    "--region", $Region,
    "--port", "8080",
    "--set-env-vars", $envVars,
    $authFlag
)

if ($CloudSqlInstance) {
    $deployArgs += @("--add-cloudsql-instances", $CloudSqlInstance)
}

gcloud @deployArgs

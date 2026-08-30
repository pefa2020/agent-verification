$ErrorActionPreference = "Stop"

if (-not $env:AWS_REGION) { throw "Set AWS_REGION" }

$ProjectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "agent-verification" }

$BuildId = aws codebuild start-build `
  --region $env:AWS_REGION `
  --project-name $ProjectName `
  --query "build.id" `
  --output text

Write-Host "Started: $BuildId"

while ($true) {
  $Status = aws codebuild batch-get-builds `
    --region $env:AWS_REGION `
    --ids $BuildId `
    --query "builds[0].buildStatus" `
    --output text

  Write-Host "Status: $Status"

  switch ($Status) {
    "SUCCEEDED" { exit 0 }
    "FAILED" { exit 1 }
    "FAULT" { exit 1 }
    "STOPPED" { exit 1 }
    "TIMED_OUT" { exit 1 }
    default { Start-Sleep -Seconds 5 }
  }
}

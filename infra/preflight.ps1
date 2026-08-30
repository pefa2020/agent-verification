$ErrorActionPreference = "Stop"

if (-not $env:AWS_REGION) { throw "Set AWS_REGION" }
if (-not $env:CODECONNECTIONS_ARN) { throw "Set CODECONNECTIONS_ARN" }

Write-Host "AWS identity:"
aws sts get-caller-identity --region $env:AWS_REGION

Write-Host ""
Write-Host "CodeConnections status:"
aws codeconnections get-connection `
  --region $env:AWS_REGION `
  --connection-arn $env:CODECONNECTIONS_ARN `
  --query "{ConnectionArn:Connection.ConnectionArn,ConnectionStatus:Connection.ConnectionStatus,ProviderType:Connection.ProviderType}" `
  --output table

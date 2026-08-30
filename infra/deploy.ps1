$ErrorActionPreference = "Stop"

if (-not $env:AWS_REGION) { throw "Set AWS_REGION" }
if (-not $env:GITHUB_REPOSITORY_URL) { throw "Set GITHUB_REPOSITORY_URL" }
if (-not $env:CODECONNECTIONS_ARN) { throw "Set CODECONNECTIONS_ARN" }

$StackName = if ($env:STACK_NAME) { $env:STACK_NAME } else { "agent-verification" }
$ProjectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "agent-verification" }

aws cloudformation deploy `
  --region $env:AWS_REGION `
  --template-file infra/codebuild.yml `
  --stack-name $StackName `
  --parameter-overrides `
    "ProjectName=$ProjectName" `
    "SourceLocation=$env:GITHUB_REPOSITORY_URL" `
    "CodeConnectionsArn=$env:CODECONNECTIONS_ARN" `
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks `
  --region $env:AWS_REGION `
  --stack-name $StackName

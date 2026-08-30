#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${GITHUB_REPOSITORY_URL:?Set GITHUB_REPOSITORY_URL}"
: "${CODECONNECTIONS_ARN:?Set CODECONNECTIONS_ARN}"

STACK_NAME="${STACK_NAME:-agent-verification}"
PROJECT_NAME="${PROJECT_NAME:-agent-verification}"

aws cloudformation deploy       --region "$AWS_REGION"       --template-file infra/codebuild.yml       --stack-name "$STACK_NAME"       --parameter-overrides         ProjectName="$PROJECT_NAME"         SourceLocation="$GITHUB_REPOSITORY_URL"         CodeConnectionsArn="$CODECONNECTIONS_ARN"       --capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks       --region "$AWS_REGION"       --stack-name "$STACK_NAME"

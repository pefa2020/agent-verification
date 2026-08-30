#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
PROJECT_NAME="${PROJECT_NAME:-agent-verification}"

BUILD_ID="$(aws codebuild start-build       --region "$AWS_REGION"       --project-name "$PROJECT_NAME"       --query 'build.id'       --output text)"

echo "Started: $BUILD_ID"

while true; do
  STATUS="$(aws codebuild batch-get-builds         --region "$AWS_REGION"         --ids "$BUILD_ID"         --query 'builds[0].buildStatus'         --output text)"

  echo "Status: $STATUS"

  case "$STATUS" in
    SUCCEEDED) exit 0 ;;
    FAILED|FAULT|STOPPED|TIMED_OUT) exit 1 ;;
    *) sleep 5 ;;
  esac
done

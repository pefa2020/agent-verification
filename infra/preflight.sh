#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${CODECONNECTIONS_ARN:?Set CODECONNECTIONS_ARN}"

echo "AWS identity:"
aws sts get-caller-identity --region "$AWS_REGION"

echo
echo "CodeConnections status:"
aws codeconnections get-connection       --region "$AWS_REGION"       --connection-arn "$CODECONNECTIONS_ARN"       --query '{ConnectionArn:Connection.ConnectionArn,ConnectionStatus:Connection.ConnectionStatus,ProviderType:Connection.ProviderType}'       --output table

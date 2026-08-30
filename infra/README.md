# Real AWS deployment

This directory contains the deployment and first-run helpers for the
actual AWS CodeBuild execution boundary.

## 1. Prerequisites

- AWS CLI installed and authenticated.
- A GitHub repository containing this project.
- An AWS CodeConnections GitHub connection authorized for that repository.
- The connection must be usable by CodeBuild.
- Permission to create/update the CloudFormation stack and IAM role.

AWS documents CodeConnections-backed GitHub access for CodeBuild and the
corresponding service-role permissions. The template scopes the connection
permissions to the supplied connection ARN.

## 2. Configure variables

Windows PowerShell:

    $env:AWS_REGION="us-east-1"
    $env:GITHUB_REPOSITORY_URL="https://github.com/OWNER/REPO"
    $env:CODECONNECTIONS_ARN="arn:aws:codeconnections:REGION:ACCOUNT:connection/ID"

Bash:

    export AWS_REGION="us-east-1"
    export GITHUB_REPOSITORY_URL="https://github.com/OWNER/REPO"
    export CODECONNECTIONS_ARN="arn:aws:codeconnections:REGION:ACCOUNT:connection/ID"

## 3. Preflight

Windows:

    .\infra\preflight.ps1

Bash:

    ./infra/preflight.sh

The preflight performs read-only checks:
- current AWS identity;
- CodeConnections ARN/status/provider.

It does not create or modify AWS resources.

## 4. Deploy

Windows:

    .\infra\deploy.ps1

Bash:

    ./infra/deploy.sh

## 5. Start the first real build

Windows:

    .\infra\run-build.ps1

Bash:

    ./infra/run-build.sh

## 6. Interpret the result

A successful CodeBuild execution means the real AWS execution environment
successfully ran the repository verification contract.

A failed build means verification evidence was produced as FAIL or the
execution itself failed. Inspect CloudWatch logs before deciding whether
the DFA should receive VERIFY_FAIL, VERIFY_BLOCKED, CANCEL, or ABORT.

Do not claim AWS end-to-end success from the local pytest count alone.

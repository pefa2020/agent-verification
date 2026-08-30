# Agent Verification v1.6

Canonical Agent Verification repository with the DFA, verification layer,
GitHub Actions, AWS CodeBuild infrastructure, deployment helpers, and a
read-only AWS preflight.

## Local verification

    python -m pytest -q

The DFA is frozen and unchanged.

## First real AWS run

Configure:

    AWS_REGION
    GITHUB_REPOSITORY_URL
    CODECONNECTIONS_ARN

Run the read-only preflight first:

    infra/preflight.ps1
    # or
    ./infra/preflight.sh

Then deploy:

    infra/deploy.ps1
    # or
    ./infra/deploy.sh

Then start CodeBuild:

    infra/run-build.ps1
    # or
    ./infra/run-build.sh

The local suite validates the deployment contract. It cannot prove that
an AWS account, GitHub connection, IAM policy, or CodeBuild build works.
Only the real AWS run can establish that external integration.

## Architecture

    ChatGPT.com
         |
       Codex
         |
      GitHub
         |
   GitHub Actions
         |
    AWS CodeBuild
         |
    Verification
         |
    normalized event
         |
        DFA

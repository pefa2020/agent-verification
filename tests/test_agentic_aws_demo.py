from verification.agentic_aws_demo import AgenticAWSVerifier
from verification.live_aws_verification import S3LiveDeploymentBoundary


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def head_object(self, **kwargs):
        body = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"ContentLength": len(body)}

    def get_caller_identity(self):
        return {"Account": "904557616330"}


class FakeResponse:
    def __init__(self, output=None, calls=None, response_id="r1"):
        self.output_text = output or "done"
        self.output = calls or []
        self.id = response_id


class FakeResponses:
    def __init__(self, call):
        self.call = call
        self.count = 0

    def create(self, **kwargs):
        self.count += 1
        if self.count == 1:
            return FakeResponse(
                calls=[self.call],
                response_id="r1",
            )
        return FakeResponse(output="deployment verified", response_id="r2")


class FakeClient:
    def __init__(self, call):
        self.responses = FakeResponses(call)


def make_boundary():
    return S3LiveDeploymentBoundary(
        account_id="904557616330",
        region="us-east-1",
        bucket="verification-test-bucket",
        key="agent-verification-v3.4.txt",
        client=FakeS3(),
    )


def test_agentic_harness_routes_model_tool_call_through_verifier():
    boundary = make_boundary()

    class Call:
        type = "function_call"
        name = "deploy"
        arguments = '{"value":"agentic-deployment"}'
        call_id = "call-1"

    verifier = AgenticAWSVerifier(
        boundary,
        client=FakeClient(Call()),
    )

    text, transcript = verifier.run("Deploy the approved artifact.")

    assert text == "deployment verified"
    assert len(transcript) == 1
    assert transcript[0]["tool"] == "deploy"
    assert transcript[0]["allowed"] is True
    assert transcript[0]["success"] is True
    assert transcript[0]["output"]["verification_success"] is True
    assert verifier.runtime.state.name == "BUILD"

from dfa.events import Event
from .result import VerificationResult, VerificationStatus

def normalize(result: VerificationResult) -> Event:
    return {
        VerificationStatus.PASS: Event.VERIFY_PASS,
        VerificationStatus.FAIL: Event.VERIFY_FAIL,
        VerificationStatus.BLOCKED: Event.VERIFY_BLOCKED,
    }[result.status]

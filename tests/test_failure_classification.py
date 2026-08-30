import pytest
from verification.failure_classification import FailureClass, FailureObservation, ClassificationError, classify_failure

def test_simple_failure():
    assert classify_failure(FailureObservation(True, executable_fix_available=True)) is FailureClass.SIMPLE

def test_ambiguity_is_drift():
    assert classify_failure(FailureObservation(True, executable_fix_available=True, requirement_ambiguity=True)) is FailureClass.INTERPRETATION_DRIFT

def test_no_fix_is_drift():
    assert classify_failure(FailureObservation(True, executable_fix_available=False)) is FailureClass.INTERPRETATION_DRIFT

def test_unavailable_is_blocked():
    assert classify_failure(FailureObservation(True, verification_unavailable=True)) is FailureClass.BLOCKED

def test_blocked_precedes_ambiguity():
    assert classify_failure(FailureObservation(True, requirement_ambiguity=True, verification_unavailable=True)) is FailureClass.BLOCKED

def test_ambiguity_precedes_no_fix():
    assert classify_failure(FailureObservation(True, requirement_ambiguity=True)) is FailureClass.INTERPRETATION_DRIFT

def test_repetition_alone_does_not_change_class():
    assert classify_failure(FailureObservation(True, executable_fix_available=True, repeated_same_failure=True)) is FailureClass.SIMPLE

def test_non_failure_rejected():
    with pytest.raises(ClassificationError):
        classify_failure(FailureObservation(False, executable_fix_available=True))

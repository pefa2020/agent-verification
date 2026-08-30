import pytest

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.user_intervention import (
    UserIntervention,
    UserInterventionError,
    UserResponseKind,
    apply_user_response,
)


def test_clarification_requires_instruction():
    response = UserIntervention(UserResponseKind.CLARIFICATION, "Use the corrected requirement")
    assert apply_user_response(response) == "Use the corrected requirement"


def test_empty_clarification_rejected():
    with pytest.raises(UserInterventionError):
        apply_user_response(UserIntervention(UserResponseKind.CLARIFICATION, "   "))


def test_cancel_is_explicit():
    assert apply_user_response(UserIntervention(UserResponseKind.CANCEL)) == "CANCEL"


def test_abort_is_explicit():
    assert apply_user_response(UserIntervention(UserResponseKind.ABORT)) == "ABORT"


def test_clarification_reenters_dfa_at_build():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)
    dfa.dispatch(Event.VERIFY_BLOCKED)
    assert dfa.state is State.USER_REQUIRED

    apply_user_response(UserIntervention(
        UserResponseKind.CLARIFICATION,
        "Clarified requirement"
    ))
    assert dfa.dispatch(Event.USER_RESPONSE) is State.BUILD


def test_cancel_from_user_required_is_terminal():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_INVALID)
    assert dfa.dispatch(Event.CANCEL) is State.ABORTED
    assert dfa.terminal


def test_abort_from_user_required_is_terminal():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_INVALID)
    assert dfa.dispatch(Event.ABORT) is State.ABORTED
    assert dfa.terminal

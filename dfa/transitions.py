from .events import Event
from .states import State

TRANSITIONS = {
    (State.REQUEST, Event.REQUEST_VALID): State.BUILD,
    (State.REQUEST, Event.REQUEST_INVALID): State.USER_REQUIRED,
    (State.REQUEST, Event.CANCEL): State.ABORTED,
    (State.REQUEST, Event.ABORT): State.ABORTED,
    (State.BUILD, Event.BUILD_READY): State.VERIFY,
    (State.BUILD, Event.BUILD_BLOCKED): State.USER_REQUIRED,
    (State.BUILD, Event.CANCEL): State.ABORTED,
    (State.BUILD, Event.ABORT): State.ABORTED,
    (State.VERIFY, Event.VERIFY_PASS): State.COMPLETE,
    (State.VERIFY, Event.VERIFY_FAIL): State.BUILD,
    (State.VERIFY, Event.VERIFY_BLOCKED): State.USER_REQUIRED,
    (State.VERIFY, Event.CANCEL): State.ABORTED,
    (State.VERIFY, Event.ABORT): State.ABORTED,
    (State.USER_REQUIRED, Event.USER_RESPONSE): State.BUILD,
    (State.USER_REQUIRED, Event.CANCEL): State.ABORTED,
    (State.USER_REQUIRED, Event.ABORT): State.ABORTED,
}

def transition(state, event):
    if state is State.COMPLETE: return State.COMPLETE
    if state is State.ABORTED: return State.ABORTED
    try: return TRANSITIONS[(state, event)]
    except KeyError as exc: raise ValueError(f"Invalid transition: {state.name} + {event.name}") from exc

from enum import Enum, auto

class Event(Enum):
    REQUEST_VALID = auto()
    REQUEST_INVALID = auto()
    BUILD_READY = auto()
    BUILD_BLOCKED = auto()
    VERIFY_PASS = auto()
    VERIFY_FAIL = auto()
    VERIFY_BLOCKED = auto()
    USER_RESPONSE = auto()
    CANCEL = auto()
    ABORT = auto()

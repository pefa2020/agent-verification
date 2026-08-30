from enum import Enum, auto

class State(Enum):
    REQUEST = auto()
    BUILD = auto()
    VERIFY = auto()
    USER_REQUIRED = auto()
    COMPLETE = auto()
    ABORTED = auto()

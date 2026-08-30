from dataclasses import dataclass
from enum import Enum


class UserResponseKind(str, Enum):
    CLARIFICATION = "CLARIFICATION"
    CANCEL = "CANCEL"
    ABORT = "ABORT"


@dataclass(frozen=True)
class UserIntervention:
    kind: UserResponseKind
    instruction: str = ""


class UserInterventionError(ValueError):
    pass


def apply_user_response(intervention: UserIntervention) -> str:
    if not isinstance(intervention, UserIntervention):
        raise UserInterventionError("invalid user intervention")

    if intervention.kind is UserResponseKind.CLARIFICATION:
        if not intervention.instruction.strip():
            raise UserInterventionError("clarification requires an instruction")
        return intervention.instruction.strip()

    if intervention.kind in {UserResponseKind.CANCEL, UserResponseKind.ABORT}:
        return intervention.kind.value

    raise UserInterventionError("unsupported user response")

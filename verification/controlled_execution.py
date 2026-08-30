from dataclasses import dataclass
from enum import Enum
from typing import Callable

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from .execution_loop import AttemptResult
from .failure_classification import FailureClass, classify_failure
from .recovery import RecoveryAction, RecoveryPolicy
from .user_intervention import UserIntervention, UserResponseKind, apply_user_response


class ControlledOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    USER_REQUIRED = "USER_REQUIRED"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class ControlledResult:
    outcome: ControlledOutcome
    attempts: int
    clarifications: int
    failure_classes: tuple[FailureClass, ...]
    state: State
    reason: str


class ControlledExecution:
    def __init__(
        self,
        attempt: Callable[[], AttemptResult],
        recovery_policy: RecoveryPolicy | None = None,
    ):
        self.attempt = attempt
        self.policy = recovery_policy or RecoveryPolicy()
        self.dfa = DFAController()
        self.failure_count = 0
        self.attempt_count = 0
        self.clarification_count = 0
        self.history: list[FailureClass] = []

    def start(self) -> None:
        if self.dfa.state is State.REQUEST:
            self.dfa.dispatch(Event.REQUEST_VALID)
            self.dfa.dispatch(Event.BUILD_READY)

    def step(
        self,
        user_response: UserIntervention | None = None,
    ) -> ControlledResult | None:
        if self.dfa.state is State.USER_REQUIRED:
            if user_response is None:
                return ControlledResult(
                    ControlledOutcome.USER_REQUIRED,
                    self.attempt_count,
                    self.clarification_count,
                    tuple(self.history),
                    self.dfa.state,
                    "awaiting explicit user response",
                )

            if user_response.kind is UserResponseKind.CLARIFICATION:
                apply_user_response(user_response)
                self.clarification_count += 1
                self.dfa.dispatch(Event.USER_RESPONSE)
                return None

            if user_response.kind is UserResponseKind.CANCEL:
                apply_user_response(user_response)
                self.dfa.dispatch(Event.CANCEL)
                return ControlledResult(
                    ControlledOutcome.ABORTED,
                    self.attempt_count,
                    self.clarification_count,
                    tuple(self.history),
                    self.dfa.state,
                    "user cancelled",
                )

            if user_response.kind is UserResponseKind.ABORT:
                apply_user_response(user_response)
                self.dfa.dispatch(Event.ABORT)
                return ControlledResult(
                    ControlledOutcome.ABORTED,
                    self.attempt_count,
                    self.clarification_count,
                    tuple(self.history),
                    self.dfa.state,
                    "user aborted",
                )

        if self.dfa.state is State.REQUEST:
            self.start()

        if self.dfa.state is State.BUILD:
            self.dfa.dispatch(Event.BUILD_READY)

        result = self.attempt()
        self.attempt_count += 1

        if result.success:
            self.dfa.dispatch(Event.VERIFY_PASS)
            return ControlledResult(
                ControlledOutcome.COMPLETE,
                self.attempt_count,
                self.clarification_count,
                tuple(self.history),
                self.dfa.state,
                "verification passed",
            )

        if result.observation is None:
            return ControlledResult(
                ControlledOutcome.USER_REQUIRED,
                self.attempt_count,
                self.clarification_count,
                tuple(self.history),
                self.dfa.state,
                "failed attempt provided no failure observation",
            )

        self.failure_count += 1
        failure_class = classify_failure(result.observation)
        self.history.append(failure_class)

        if failure_class is FailureClass.BLOCKED:
            self.dfa.dispatch(Event.VERIFY_BLOCKED)
            return ControlledResult(
                ControlledOutcome.USER_REQUIRED,
                self.attempt_count,
                self.clarification_count,
                tuple(self.history),
                self.dfa.state,
                "verification blocked",
            )

        if failure_class is FailureClass.INTERPRETATION_DRIFT:
            self.dfa.dispatch(Event.VERIFY_BLOCKED)
            return ControlledResult(
                ControlledOutcome.USER_REQUIRED,
                self.attempt_count,
                self.clarification_count,
                tuple(self.history),
                self.dfa.state,
                "interpretation drift requires clarification",
            )

        decision = self.policy.decide(failure_class, self.failure_count)
        self.dfa.dispatch(Event.VERIFY_FAIL)

        if decision.action is RecoveryAction.RETRY:
            return None

        # The DFA's VERIFY_FAIL transition has already returned to BUILD.
        # Move through BUILD_READY then VERIFY_BLOCKED to expose the
        # USER_REQUIRED boundary without inventing a new DFA state.
        self.dfa.dispatch(Event.BUILD_READY)
        self.dfa.dispatch(Event.VERIFY_BLOCKED)
        return ControlledResult(
            ControlledOutcome.USER_REQUIRED,
            self.attempt_count,
            self.clarification_count,
            tuple(self.history),
            self.dfa.state,
            decision.reason,
        )

    def run(
        self,
        responses: list[UserIntervention] | None = None,
    ) -> ControlledResult:
        self.start()
        responses = list(responses or [])
        response_index = 0

        while True:
            result = self.step()

            if result is None:
                continue

            if (
                result.outcome is ControlledOutcome.USER_REQUIRED
                and self.dfa.state is State.USER_REQUIRED
                and response_index < len(responses)
            ):
                response = responses[response_index]
                response_index += 1
                resumed = self.step(response)
                if resumed is None:
                    continue
                return resumed

            return result

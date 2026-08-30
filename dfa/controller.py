from dataclasses import dataclass
from .events import Event
from .states import State
from .transitions import transition

@dataclass
class DFAController:
    state: State = State.REQUEST

    def dispatch(self, event: Event) -> State:
        self.state = transition(self.state, event)
        return self.state

    @property
    def accepting(self) -> bool:
        return self.state is State.COMPLETE

    @property
    def terminal(self) -> bool:
        return self.state in {State.COMPLETE, State.ABORTED}

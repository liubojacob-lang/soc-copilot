"""State machine for DAG node execution states."""

from enum import Enum


class NodeState(str, Enum):
    """Possible states for a DAG node during execution."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


# Valid state transitions
VALID_TRANSITIONS: dict[NodeState, set[NodeState]] = {
    NodeState.PENDING: {NodeState.QUEUED, NodeState.SKIPPED, NodeState.CANCELLED},
    NodeState.QUEUED: {NodeState.RUNNING, NodeState.CANCELLED, NodeState.SKIPPED},
    NodeState.RUNNING: {
        NodeState.SUCCESS,
        NodeState.FAILED,
        NodeState.WAITING_APPROVAL,
        NodeState.TIMEOUT,
        NodeState.CANCELLED,
    },
    NodeState.WAITING_APPROVAL: {
        NodeState.RUNNING,
        NodeState.CANCELLED,
        NodeState.FAILED,
    },
    NodeState.SUCCESS: set(),
    NodeState.FAILED: set(),
    NodeState.CANCELLED: set(),
    NodeState.TIMEOUT: set(),
    NodeState.SKIPPED: set(),
}


class NodeStateMachine:
    """State machine for managing node execution state transitions."""

    def __init__(self, initial_state: NodeState = NodeState.PENDING):
        """Initialize the state machine with an initial state.

        Args:
            initial_state: Starting state for the node
        """
        self._state = initial_state
        self._history: list[tuple[NodeState, NodeState]] = []

    @property
    def state(self) -> NodeState:
        """Get the current state."""
        return self._state

    @property
    def history(self) -> list[tuple[NodeState, NodeState]]:
        """Get the state transition history."""
        return self._history.copy()

    def transition_to(self, new_state: NodeState) -> bool:
        """Transition to a new state if valid.

        Args:
            new_state: Target state to transition to

        Returns:
            True if transition was successful, False otherwise

        Raises:
            ValueError: If the transition is invalid
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition from {self._state.value} to {new_state.value}. "
                f"Valid transitions: {[s.value for s in VALID_TRANSITIONS.get(self._state, set())]}"
            )

        old_state = self._state
        self._state = new_state
        self._history.append((old_state, new_state))
        return True

    def can_transition_to(self, new_state: NodeState) -> bool:
        """Check if a transition to the given state is valid.

        Args:
            new_state: Target state to check

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_targets

    def is_terminal(self) -> bool:
        """Check if the current state is terminal (no further transitions).

        Returns:
            True if in a terminal state, False otherwise
        """
        return len(VALID_TRANSITIONS.get(self._state, set())) == 0

    def is_executing(self) -> bool:
        """Check if the node is currently in an executing state.

        Returns:
            True if executing, False otherwise
        """
        return self._state in {
            NodeState.QUEUED,
            NodeState.RUNNING,
            NodeState.WAITING_APPROVAL,
        }

    def is_finished(self) -> bool:
        """Check if the node has finished execution (success or failure).

        Returns:
            True if finished, False otherwise
        """
        return self._state in {
            NodeState.SUCCESS,
            NodeState.FAILED,
            NodeState.CANCELLED,
            NodeState.TIMEOUT,
            NodeState.SKIPPED,
        }

    def reset(self) -> None:
        """Reset the state machine to PENDING."""
        self._state = NodeState.PENDING
        self._history.clear()


def validate_state_transition(from_state: str, to_state: str) -> bool:
    """Validate a state transition between string states.

    Args:
        from_state: Source state as string
        to_state: Target state as string

    Returns:
        True if the transition is valid, False otherwise
    """
    try:
        from_node = NodeState(from_state)
        to_node = NodeState(to_state)
        machine = NodeStateMachine(from_node)
        return machine.can_transition_to(to_node)
    except (ValueError, KeyError):
        return False

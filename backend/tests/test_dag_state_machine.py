"""Unit tests for the DAG node state machine."""

import pytest

from playbook_engine.dag.state_machine import (
    NodeState,
    NodeStateMachine,
    validate_state_transition,
)

pytestmark = [pytest.mark.unit]


class TestNodeStateMachine:
    def test_starts_in_pending(self):
        machine = NodeStateMachine()
        assert machine.state == NodeState.PENDING

    def test_custom_initial_state(self):
        machine = NodeStateMachine(NodeState.RUNNING)
        assert machine.state == NodeState.RUNNING

    def test_happy_path_transitions(self):
        machine = NodeStateMachine()
        assert machine.transition_to(NodeState.QUEUED) is True
        assert machine.transition_to(NodeState.RUNNING) is True
        assert machine.transition_to(NodeState.SUCCESS) is True
        assert machine.state == NodeState.SUCCESS

    def test_invalid_transition_raises(self):
        machine = NodeStateMachine()
        with pytest.raises(ValueError, match="Invalid state transition"):
            machine.transition_to(NodeState.SUCCESS)

    def test_running_to_waiting_approval(self):
        machine = NodeStateMachine(NodeState.RUNNING)
        assert machine.transition_to(NodeState.WAITING_APPROVAL) is True
        assert machine.is_executing() is True
        assert machine.transition_to(NodeState.RUNNING) is True

    def test_history_records_transitions(self):
        machine = NodeStateMachine()
        machine.transition_to(NodeState.QUEUED)
        machine.transition_to(NodeState.RUNNING)
        assert machine.history == [
            (NodeState.PENDING, NodeState.QUEUED),
            (NodeState.QUEUED, NodeState.RUNNING),
        ]

    def test_history_is_a_copy(self):
        machine = NodeStateMachine()
        machine.transition_to(NodeState.QUEUED)
        machine.history.append(("bogus", "bogus"))
        assert len(machine.history) == 1

    def test_terminal_states(self):
        for terminal in (
            NodeState.SUCCESS,
            NodeState.FAILED,
            NodeState.CANCELLED,
            NodeState.TIMEOUT,
            NodeState.SKIPPED,
        ):
            machine = NodeStateMachine(terminal)
            assert machine.is_terminal() is True
            assert machine.is_finished() is True
            assert machine.is_executing() is False

    def test_pending_is_not_terminal(self):
        machine = NodeStateMachine()
        assert machine.is_terminal() is False
        assert machine.is_finished() is False

    def test_reset(self):
        machine = NodeStateMachine()
        machine.transition_to(NodeState.QUEUED)
        machine.reset()
        assert machine.state == NodeState.PENDING
        assert machine.history == []

    def test_can_transition_to(self):
        machine = NodeStateMachine(NodeState.RUNNING)
        assert machine.can_transition_to(NodeState.SUCCESS) is True
        assert machine.can_transition_to(NodeState.QUEUED) is False


class TestValidateStateTransition:
    def test_valid_transition(self):
        assert validate_state_transition("pending", "queued") is True
        assert validate_state_transition("running", "failed") is True

    def test_invalid_transition(self):
        assert validate_state_transition("success", "running") is False
        assert validate_state_transition("pending", "success") is False

    def test_unknown_state_returns_false(self):
        assert validate_state_transition("bogus", "queued") is False
        assert validate_state_transition("pending", "bogus") is False

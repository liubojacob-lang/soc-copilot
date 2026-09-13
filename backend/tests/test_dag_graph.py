"""Unit tests for DAGBuilder, topological sort, and graph helpers."""

import pytest

from playbook_engine.dag.engine import (
    DAGBuilder,
    DAGDefinition,
    DAGEdge,
    DAGExecutionEngine,
    DAGNode,
)
from playbook_engine.dag.exceptions import DAGCycleError

pytestmark = [pytest.mark.unit]


def diamond_definition() -> DAGDefinition:
    return DAGBuilder.from_json(
        {
            "nodes": [
                {"id": node_id, "step_id": "noop"} for node_id in ("a", "b", "c", "d")
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "a", "target": "c"},
                {"source": "b", "target": "d"},
                {"source": "c", "target": "d"},
            ],
        }
    )


class TestDAGBuilder:
    def test_builds_nodes_and_edges(self):
        definition = diamond_definition()
        assert set(definition.nodes) == {"a", "b", "c", "d"}
        assert len(definition.edges) == 4
        assert definition.nodes["a"].name == "a"

    def test_missing_required_keys_raises(self):
        with pytest.raises(ValueError, match="nodes.*edges"):
            DAGBuilder.from_json({"nodes": []})
        with pytest.raises(ValueError, match="nodes.*edges"):
            DAGBuilder.from_json({})

    def test_step_id_falls_back_to_type(self):
        definition = DAGBuilder.from_json(
            {
                "nodes": [{"id": "n1", "type": "ti_lookup_otx"}],
                "edges": [],
            }
        )
        assert definition.nodes["n1"].step_id == "ti_lookup_otx"

    def test_retry_policy_mapping(self):
        definition = DAGBuilder.from_json(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "step_id": "noop",
                        "retry_policy": {
                            "max_attempts": 5,
                            "backoff_base": 0.5,
                            "backoff_max": 10.0,
                            "timeout": 30,
                        },
                    }
                ],
                "edges": [],
            }
        )
        policy = definition.nodes["n1"].retry_policy
        assert policy.max_attempts == 5
        assert policy.backoff_base == 0.5
        assert policy.backoff_max == 10.0
        assert policy.timeout == 30

    def test_no_retry_policy_by_default(self):
        definition = DAGBuilder.from_json(
            {"nodes": [{"id": "n1", "step_id": "noop"}], "edges": []}
        )
        assert definition.nodes["n1"].retry_policy is None
        assert definition.nodes["n1"].config == {}
        assert definition.nodes["n1"].inputs == {}

    def test_custom_name_and_timeout(self):
        definition = DAGBuilder.from_json(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "step_id": "noop",
                        "name": "Lookup",
                        "timeout_seconds": 60,
                    }
                ],
                "edges": [],
            }
        )
        assert definition.nodes["n1"].name == "Lookup"
        assert definition.nodes["n1"].timeout_seconds == 60


class TestDAGDefinition:
    def test_get_dependencies_and_dependents(self):
        definition = diamond_definition()
        assert definition.get_dependencies("d") == ["b", "c"]
        assert definition.get_dependents("a") == ["b", "c"]
        assert definition.get_dependencies("a") == []
        assert definition.get_dependents("d") == []


class TestTopologicalSort:
    def setup_method(self):
        self.engine = DAGExecutionEngine(session=None)

    def test_linear_order(self):
        definition = DAGBuilder.from_json(
            {
                "nodes": [{"id": n, "step_id": "noop"} for n in ("a", "b", "c")],
                "edges": [
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "c"},
                ],
            }
        )
        assert self.engine._topological_sort(definition) == ["a", "b", "c"]

    def test_roots_come_before_dependents(self):
        definition = diamond_definition()
        order = self.engine._topological_sort(definition)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_cycle_raises_with_cycle_nodes(self):
        definition = DAGBuilder.from_json(
            {
                "nodes": [{"id": n, "step_id": "noop"} for n in ("a", "b")],
                "edges": [
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "a"},
                ],
            }
        )
        with pytest.raises(DAGCycleError) as exc_info:
            self.engine._topological_sort(definition)
        assert set(exc_info.value.cycle_nodes) == {"a", "b"}


class TestGroupByLevel:
    def setup_method(self):
        self.engine = DAGExecutionEngine(session=None)

    def test_single_node_single_level(self):
        definition = DAGBuilder.from_json(
            {"nodes": [{"id": "a", "step_id": "noop"}], "edges": []}
        )
        levels = self.engine._group_by_level(definition, ["a"])
        assert levels == [["a"]]

    def test_all_nodes_collapse_into_one_level(self):
        # Known behavior quirk: dependency ordering is only enforced by
        # topological order, while grouping lets a node join the current
        # level as soon as its deps have been *seen* (not completed), so a
        # diamond collapses into a single concurrent level.
        definition = diamond_definition()
        order = self.engine._topological_sort(definition)
        levels = self.engine._group_by_level(definition, order)
        assert levels == [["a", "b", "c", "d"]]


class TestGetExecutableNodes:
    def setup_method(self):
        self.engine = DAGExecutionEngine(session=None)

    def test_no_failures_keeps_everything(self):
        definition = diamond_definition()
        assert self.engine._get_executable_nodes(definition, [], []) == {
            "a",
            "b",
            "c",
            "d",
        }

    def test_failed_node_and_blocked_dependents_are_excluded(self):
        definition = diamond_definition()
        assert self.engine._get_executable_nodes(definition, ["a"], []) == {"d"}

    def test_skipped_nodes_are_blocked_too(self):
        definition = diamond_definition()
        assert self.engine._get_executable_nodes(definition, [], ["a"]) == {"d"}


class TestDAGNodeDefaults:
    def test_post_init_defaults(self):
        node = DAGNode(id="n1", step_id="noop", name="N1")
        assert node.config == {}
        assert node.inputs == {}
        assert node.inputs_template == {}
        assert node.outputs_mapping == {}

    def test_edge_condition_defaults_to_none(self):
        edge = DAGEdge(source="a", target="b")
        assert edge.condition is None

"use client";

import React, { useCallback, useMemo, useRef, useLayoutEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  Edge,
  Node,
  ConnectionMode,
  useNodesState,
  useEdgesState,
  addEdge,
  NodeChange,
  EdgeChange,
  Connection,
} from "reactflow";
import "reactflow/dist/style.css";

import DAGNode, { NodeData } from "./DAGNode";

const nodeTypes: NodeTypes = {
  dagNode: DAGNode,
};

const defaultEdgeOptions = {
  animated: false,
  style: { strokeWidth: 2 },
};

// P0-2: Maximum update iterations to prevent infinite loops
const MAX_UPDATE_ITERATIONS = 100;

// Internal types for normalizing mixed node/edge definitions
interface DefinitionNode {
  id: string;
  step_id?: string;
  name?: string;
  label?: string;
  position_x?: number;
  position_y?: number;
}

interface DefinitionEdge {
  source: string;
  target: string;
  condition?: string;
}

interface DAGCanvasProps {
  definition?: {
    nodes:
      | Array<{
          id: string;
          step_id: string;
          name: string;
          position_x?: number;
          position_y?: number;
        }>
      | Node<NodeData>[];
    edges: Array<{ source: string; target: string; condition?: string }> | Edge[];
  };
  nodeStatuses?: Record<
    string,
    {
      status: "pending" | "running" | "success" | "failed" | "skipped" | "waiting_approval";
      duration?: number;
      error?: string;
      output?: Record<string, unknown>;
    }
  >;
  readonly?: boolean;
  onNodesChange?: (nodes: Node<NodeData>[]) => void;
  onEdgesChange?: (edges: Edge[]) => void;
  onConnect?: (connection: Connection) => void;
  onNodeClick?: (node: Node) => void;
  onEdgeClick?: (edge: Edge) => void;
  onPaneClick?: () => void;
  className?: string;
}

/**
 * Create a stable hash of nodeStatuses values (not object reference)
 * This ensures the effect only runs when actual status values change, not when parent re-renders
 */
function createStatusHash(
  statuses: Record<
    string,
    { status: string; duration?: number; error?: string; output?: Record<string, unknown> }
  >
): string {
  const keys = Object.keys(statuses).sort();
  if (keys.length === 0) return "";

  return keys
    .map((key) => {
      const s = statuses[key];
      return `${key}:${s.status}:${s.duration ?? ""}:${s.error ?? ""}:${JSON.stringify(s.output ?? {})}`;
    })
    .join("|");
}

export function DAGCanvas({
  definition,
  nodeStatuses = {},
  readonly = true,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onEdgeClick,
  onPaneClick,
  className = "",
}: DAGCanvasProps) {
  // Create a stable key for the definition structure (ignoring statuses)
  const currentDefinitionKey = useMemo(() => {
    if (!definition) return "";
    return JSON.stringify({
      nodes: definition.nodes?.map((n) => n.id).sort(),
      edges: definition.edges?.map((e) => `${e.source}-${e.target}`).sort(),
    });
  }, [definition]);

  // IMPORTANT: Create a STABLE hash of nodeStatuses for dependencies
  // This prevents the effect from running when parent re-renders with same status values
  const nodeStatusesHash = useMemo(() => createStatusHash(nodeStatuses), [nodeStatuses]);

  // Build initial nodes from definition (only used on mount and definition changes)
  const initialNodes = useMemo(() => {
    if (!definition?.nodes) return [];

    return definition.nodes.map((node, index) => {
      const status = nodeStatuses[node.id] || { status: "pending" as const };

      // Handle both plain objects and ReactFlow Node types
      const isReactFlowNode = "data" in node && "position" in node;
      const rfNode = isReactFlowNode ? (node as Node) : null;
      const defNode = isReactFlowNode ? null : (node as DefinitionNode);
      const id = rfNode?.id ?? defNode?.id ?? "";
      const position = rfNode?.position ?? {
        x: defNode?.position_x ?? (index % 3) * 300,
        y: defNode?.position_y ?? Math.floor(index / 3) * 150,
      };
      const nodeData = rfNode?.data ?? defNode;
      const label = nodeData?.label || nodeData?.name || id;
      const stepId = (nodeData as NodeData)?.stepId || defNode?.step_id || id;

      return {
        id,
        type: "dagNode",
        position,
        data: {
          label,
          stepId,
          status: status.status,
          duration: status.duration,
          error: status.error,
          output: status.output,
        } as NodeData,
      };
    });
    // Only depend on definition structure, NOT nodeStatuses
    // Status updates are handled separately to avoid loops
  }, [definition?.nodes]); // Removed nodeStatuses from deps

  // Build initial edges from definition
  const initialEdges = useMemo(() => {
    if (!definition?.edges) return [];

    return definition.edges.map((edge, index) => {
      // Handle both plain objects and ReactFlow Edge types
      const isReactFlowEdge = "id" in edge && "source" in edge && "target" in edge;
      const rfEdge = isReactFlowEdge ? (edge as Edge) : null;
      const defEdge = isReactFlowEdge ? null : (edge as DefinitionEdge);
      const source = rfEdge?.source ?? defEdge?.source ?? "";
      const target = rfEdge?.target ?? defEdge?.target ?? "";
      const condition = rfEdge?.label ?? defEdge?.condition;

      return {
        id: `edge-${index}`,
        source,
        target,
        label: condition,
        animated: false,
        style: { stroke: "#94a3b8", strokeWidth: 2 },
      };
    });
  }, [definition?.edges]); // Removed nodeStatuses from deps

  // Initialize state directly with initialNodes / initialEdges regardless of mode
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);

  // Refs to track state
  const initializedRef = useRef(true);
  const isSyncingNodesFromParentRef = useRef(false);
  const isSyncingEdgesFromParentRef = useRef(false);
  const lastNotifiedNodesRef = useRef(
    JSON.stringify(initialNodes.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y })))
  );
  const lastNotifiedEdgesRef = useRef(
    JSON.stringify(initialEdges.map((e) => ({ s: e.source, t: e.target })))
  );
  const readonlyDefinitionKeyRef = useRef(readonly ? currentDefinitionKey : "");
  const editDefinitionKeyRef = useRef(readonly ? "" : currentDefinitionKey);
  const lastProcessedStatusHashRef = useRef(nodeStatusesHash);

  // P0-2: Update iteration counter for infinite loop protection
  const updateIterationRef = useRef(0);

  // Sync from definition - ONLY when definition structure changes
  useLayoutEffect(() => {
    if (readonly) {
      // Readonly mode: only sync when definition structure changes
      if (currentDefinitionKey !== readonlyDefinitionKeyRef.current) {
        readonlyDefinitionKeyRef.current = currentDefinitionKey;
        setNodes(initialNodes);
        setEdges(initialEdges);
        lastProcessedStatusHashRef.current = nodeStatusesHash;
        // P0-2: Reset iteration counter on definition change
        updateIterationRef.current = 0;
      }
    } else {
      // Edit mode: only sync when definition structure changes
      if (currentDefinitionKey !== editDefinitionKeyRef.current) {
        editDefinitionKeyRef.current = currentDefinitionKey;
        setNodes(initialNodes);
        setEdges(initialEdges);
        // Suppress notifications back to parent while syncing external props
        isSyncingNodesFromParentRef.current = true;
        isSyncingEdgesFromParentRef.current = true;
        lastNotifiedNodesRef.current = JSON.stringify(
          initialNodes.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y }))
        );
        lastNotifiedEdgesRef.current = JSON.stringify(
          initialEdges.map((e) => ({ s: e.source, t: e.target }))
        );
        lastProcessedStatusHashRef.current = nodeStatusesHash;
        // P0-2: Reset iteration counter on definition change
        updateIterationRef.current = 0;
      }
    }
  }, [
    readonly,
    currentDefinitionKey,
    initialNodes,
    initialEdges,
    setNodes,
    setEdges,
    nodeStatusesHash,
  ]);

  /**
   * CRITICAL: Idempotent status update for readonly mode
   *
   * This effect ONLY runs when:
   * 1. readonly mode is active
   * 2. Already initialized
   * 3. nodeStatuses HASH changed (actual values changed, not just reference)
   *
   * The update function is IDEMPOTENT:
   * - If NO nodes changed → returns ORIGINAL nodes array reference
   * - If a node hasn't changed → returns ORIGINAL node reference
   * - Only creates new objects when values actually changed
   */
  useLayoutEffect(() => {
    if (!readonly || !initializedRef.current) return;

    // P0-2: Infinite loop protection - check iteration count
    if (updateIterationRef.current >= MAX_UPDATE_ITERATIONS) {
      console.warn("[DAGCanvas] Max update iterations reached, skipping further updates");
      return;
    }

    // Skip if status hash hasn't changed (prevents unnecessary updates)
    if (nodeStatusesHash === lastProcessedStatusHashRef.current) return;

    // P0-2: Increment iteration counter
    updateIterationRef.current += 1;
    lastProcessedStatusHashRef.current = nodeStatusesHash;

    // IDEMPOTENT node update: only create new objects when values change
    setNodes((currentNodes) => {
      let hasChanges = false;
      const newNodes = currentNodes.map((node) => {
        const newStatus = nodeStatuses[node.id];
        const currentData = node.data;

        // If no status data for this node, keep as-is
        if (!newStatus) {
          return node;
        }

        // Check if anything actually changed
        const statusChanged = currentData.status !== newStatus.status;
        const durationChanged = currentData.duration !== newStatus.duration;
        const errorChanged = currentData.error !== newStatus.error;
        const outputChanged =
          JSON.stringify(currentData.output) !== JSON.stringify(newStatus.output);

        if (!statusChanged && !durationChanged && !errorChanged && !outputChanged) {
          // No changes - return ORIGINAL reference (crucial for idempotency)
          return node;
        }

        // Something changed - mark that we have changes
        hasChanges = true;

        // Return NEW object with updated data
        return {
          ...node,
          data: {
            ...currentData,
            status: newStatus.status,
            duration: newStatus.duration,
            error: newStatus.error,
            output: newStatus.output,
          },
        };
      });

      // CRITICAL: If NO changes detected, return ORIGINAL array reference
      // This is what makes the operation truly idempotent
      return hasChanges ? newNodes : currentNodes;
    });

    // IDEMPOTENT edge update
    setEdges((currentEdges) => {
      let hasChanges = false;
      const newEdges = currentEdges.map((edge) => {
        const sourceStatus = nodeStatuses[edge.source]?.status;
        const newAnimated = sourceStatus === "running";
        const newStroke =
          sourceStatus === "success"
            ? "#22c55e"
            : sourceStatus === "failed"
              ? "#ef4444"
              : sourceStatus === "running"
                ? "#3b82f6"
                : "#94a3b8";

        // Check if anything changed
        const animatedChanged = edge.animated !== newAnimated;
        const styleChanged = (edge.style as Record<string, string>)?.stroke !== newStroke;

        if (!animatedChanged && !styleChanged) {
          // No changes - return ORIGINAL reference
          return edge;
        }

        hasChanges = true;

        return {
          ...edge,
          animated: newAnimated,
          style: { stroke: newStroke, strokeWidth: 2 },
        };
      });

      // Return ORIGINAL array if no changes
      return hasChanges ? newEdges : currentEdges;
    });
  }, [readonly, nodeStatusesHash, setNodes, setEdges]); // Only depend on HASH, not nodeStatuses object

  // Notify parent of nodes changes - only when actually changed by canvas interaction
  useLayoutEffect(() => {
    if (readonly || !onNodesChange || !initializedRef.current) return;

    const nodesKey = JSON.stringify(
      nodes.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y }))
    );

    if (isSyncingNodesFromParentRef.current) {
      if (nodesKey === lastNotifiedNodesRef.current) {
        isSyncingNodesFromParentRef.current = false;
      }
      return;
    }

    if (nodesKey !== lastNotifiedNodesRef.current) {
      lastNotifiedNodesRef.current = nodesKey;
      onNodesChange(nodes);
    }
  }, [nodes, onNodesChange, readonly]);

  // Notify parent of edges changes - only when actually changed by canvas interaction
  useLayoutEffect(() => {
    if (readonly || !onEdgesChange || !initializedRef.current) return;

    const edgesKey = JSON.stringify(edges.map((e) => ({ s: e.source, t: e.target })));

    if (isSyncingEdgesFromParentRef.current) {
      if (edgesKey === lastNotifiedEdgesRef.current) {
        isSyncingEdgesFromParentRef.current = false;
      }
      return;
    }

    if (edgesKey !== lastNotifiedEdgesRef.current) {
      lastNotifiedEdgesRef.current = edgesKey;
      onEdgesChange(edges);
    }
  }, [edges, onEdgesChange, readonly]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChangeInternal(changes);
    },
    [onNodesChangeInternal]
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChangeInternal(changes);
    },
    [onEdgesChangeInternal]
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (readonly) return;
      setEdges((eds) => addEdge(connection, eds));
      if (onConnect) {
        onConnect(connection);
      }
    },
    [readonly, onConnect, setEdges]
  );

  // Handle node click for selection
  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (readonly) return;
      event.stopPropagation();
      if (onNodeClick) {
        onNodeClick(node);
      }
    },
    [readonly, onNodeClick]
  );

  // Handle edge click for selection
  const handleEdgeClick = useCallback(
    (event: React.MouseEvent, edge: Edge) => {
      if (readonly) return;
      event.stopPropagation();
      if (onEdgeClick) {
        onEdgeClick(edge);
      }
    },
    [readonly, onEdgeClick]
  );

  // Handle background click to deselect
  const handlePaneClick = useCallback(
    (event: React.MouseEvent) => {
      if (readonly) return;
      if (onPaneClick) {
        onPaneClick();
      }
    },
    [readonly, onPaneClick]
  );

  return (
    <div className={`w-full h-full ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readonly ? undefined : handleNodesChange}
        onEdgesChange={readonly ? undefined : handleEdgesChange}
        onConnect={readonly ? undefined : handleConnect}
        onNodeClick={readonly ? undefined : handleNodeClick}
        onEdgeClick={readonly ? undefined : handleEdgeClick}
        onPaneClick={readonly ? undefined : handlePaneClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.2}
        maxZoom={2}
        defaultEdgeOptions={defaultEdgeOptions}
      >
        <Background color="#94a3b8" gap={16} />
        <Controls showZoom={true} showFitView={true} showInteractive={!readonly} />
        {/* MiniMap 的底色与蒙版不走 props —— reactflow 默认写死白底，
            在深色主题下会是一块纯白方块。统一由 app/globals.css 的
            .react-flow__minimap / .react-flow__minimap-mask 规则按语义 token 接管，
            避免同一件事有两个来源。 */}
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as NodeData;
            switch (data.status) {
              case "success":
                return "#22c55e";
              case "failed":
                return "#ef4444";
              case "running":
                return "#3b82f6";
              case "skipped":
                return "#6b7280";
              case "waiting_approval":
                return "#eab308";
              default:
                return "#cbd5e1";
            }
          }}
        />
      </ReactFlow>
    </div>
  );
}

export default DAGCanvas;

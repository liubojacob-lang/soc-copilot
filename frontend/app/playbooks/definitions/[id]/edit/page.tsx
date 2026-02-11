"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { api, api_v7 } from "@/lib/api";
import { loadAuthState, logout } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { DAGCanvas } from "@/components/dag";
import { Save, ArrowLeft, Play, Plus, Trash2, Settings } from "lucide-react";
import { Node, Edge } from "reactflow";

// Available node types
const NODE_TYPES = [
  { id: "manual_trigger", name: "Manual Trigger", category: "trigger" },
  { id: "extract_iocs", name: "Extract IOCs", category: "action" },
  { id: "ti_lookup_otx", name: "OTX Lookup", category: "enrichment" },
  { id: "normalize", name: "Normalize", category: "action" },
  { id: "decision", name: "Decision", category: "logic" },
  { id: "http_request", name: "HTTP Request", category: "action" },
  { id: "slack_notify", name: "Slack Notify", category: "notification" },
  { id: "sleep", name: "Sleep", category: "utility" },
  { id: "risk_score", name: "Risk Score", category: "analysis" },
  { id: "action_plan", name: "Action Plan", category: "analysis" },
];

interface PlaybookDefinition {
  id: string;
  name: string;
  version: string;
  description?: string;
  status?: "draft" | "published" | "archived";
  definition_json?: {
    nodes: Array<any>;
    edges: Array<any>;
    global_context?: Record<string, any>;
  };
  dag?: {
    nodes: Array<any>;
    edges: Array<any>;
  };
}

export default function EditPlaybookDefinitionPage() {
  const router = useRouter();
  const params = useParams();
  const definitionId = params.id as string;

  const [definition, setDefinition] = useState<PlaybookDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Editable DAG state
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [showNodePanel, setShowNodePanel] = useState(false);
  const [showNodeTypeSelector, setShowNodeTypeSelector] = useState(false);
  const [definitionLoadedAt, setDefinitionLoadedAt] = useState<number>(0);

  useEffect(() => {
    setMounted(true);

    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push("/login");
      return;
    }

    loadDefinition();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [definitionId]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  // Define callbacks BEFORE early returns to maintain consistent hook order
  const handleNodesChange = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
  }, []);

  const handleEdgesChange = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
  }, []);

  const handleConnect = useCallback((connection: Edge) => {
    setEdges((eds) => [...eds, { ...connection, id: `edge-${eds.length}` }]);
  }, []);

  const handleDeleteSelected = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
      setSelectedNode(null);
    }
    if (selectedEdge) {
      setEdges((eds) => eds.filter((e) => e.id !== selectedEdge.id));
      setSelectedEdge(null);
    }
  }, [selectedNode, selectedEdge]);

  const handleAddNode = useCallback((nodeType: string) => {
    const newNodeId = `${nodeType}-${Date.now()}`;
    const nodeTypeInfo = NODE_TYPES.find(t => t.id === nodeType);
    setNodes((nds) => [...nds, {
      id: newNodeId,
      type: "dagNode",
      position: { x: 100 + (nds.length % 3) * 300, y: 100 + Math.floor(nds.length / 3) * 150 },
      data: {
        label: nodeTypeInfo?.name || nodeType,
        stepId: nodeType,
        stepType: nodeType,
      },
    }]);
    setShowNodeTypeSelector(false);
  }, []);

  const handleUpdateNode = useCallback((nodeId: string, updates: Partial<Node>) => {
    setNodes((nds) => nds.map((n) => n.id === nodeId ? { ...n, ...updates } : n));
  }, []);

  // Memoize dag definition to prevent unnecessary re-renders of DAGCanvas
  const dagDefinition = useMemo(() => ({ nodes, edges }), [nodes, edges]);

  if (!mounted) return null;

  async function loadDefinition() {
    setLoading(true);
    setError(null);
    try {
      const def: any = await api_v7.getDefinition(definitionId);

      // Check if definition can be edited (only draft status)
      if (def.status && def.status !== "draft") {
        setError(`Cannot edit ${def.status} definition. Only draft definitions can be edited.`);
        setLoading(false);
        return;
      }

      setDefinition(def);

      // Initialize nodes and edges from definition
      const dag = def.definition_json || def.dag || { nodes: [], edges: [] };
      if (dag.nodes) {
        setNodes(dag.nodes.map((node: any, index: number) => ({
          id: node.id,
          type: "dagNode",
          position: {
            x: node.position_x ?? (index % 3) * 300,
            y: node.position_y ?? Math.floor(index / 3) * 150,
          },
          data: {
            label: node.name || node.id,
            stepId: node.step_id || node.type || "manual_trigger",
            stepType: node.step_id || node.type || "manual_trigger",
          },
        })));
      }
      if (dag.edges) {
        setEdges(dag.edges.map((edge: any, index: number) => ({
          id: edge.id || `edge-${index}`,
          source: edge.source,
          target: edge.target,
          label: edge.condition,
          type: edge.condition ? "smoothstep" : "default",
        })));
      }
      // Set timestamp to mark definition as loaded
      setDefinitionLoadedAt(Date.now());
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to load definition");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      // Convert nodes back to definition format (DAGNode: id, name, type, step_id, position_x/y)
      const updatedNodes = nodes.map((node) => ({
        id: node.id,
        name: (node.data as any)?.label || node.id,
        type: (node.data as any)?.stepType || "manual_trigger",
        step_id: (node.data as any)?.stepId || node.id,
        position_x: node.position.x,
        position_y: node.position.y,
      }));

      // Convert edges back to definition format (condition 须为 string)
      const updatedEdges = edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        condition: typeof edge.label === "string" ? edge.label : undefined,
      }));

      await api_v7.updateDefinition(definitionId, {
        dag: { nodes: updatedNodes, edges: updatedEdges },
      });
      router.push(`/playbooks/definitions/${definitionId}`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to save definition");
    } finally {
      setSaving(false);
    }
  }

  async function handleRun() {
    try {
      const result = await api.executeDAGDefinition(definitionId, "dry_run");
      router.push(`/playbooks/${result.run_id}`);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "Failed to execute playbook");
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation title="Edit Playbook Definition" subtitle="Modify DAG workflow" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading definition...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error && definition === null) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation title="Edit Playbook Definition" subtitle="Modify DAG workflow" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
            {error}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation title="Edit Playbook Definition" subtitle="Modify DAG workflow" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <button
                onClick={() => router.push(`/playbooks/definitions/${definitionId}`)}
                className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Definition
              </button>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{definition?.name}</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Version {definition?.version}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => router.push(`/playbooks/definitions/${definitionId}`)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRun}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Play className="w-5 h-5" />
                Test Run
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                <Save className="w-5 h-5" />
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>

          {definition?.description && (
            <p className="mt-4 text-gray-600 dark:text-gray-400">{definition.description}</p>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* DAG Editor */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Workflow Editor</h2>
            <div className="flex gap-2">
              {(selectedNode || selectedEdge) && (
                <button
                  onClick={handleDeleteSelected}
                  className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Selected
                </button>
              )}
              <div className="relative">
                <button
                  onClick={() => setShowNodeTypeSelector(!showNodeTypeSelector)}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                >
                  <Plus className="w-4 h-4" />
                  Add Node
                </button>
                {showNodeTypeSelector && (
                  <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
                    <div className="p-2">
                      {NODE_TYPES.map((nodeType) => (
                        <button
                          key={nodeType.id}
                          onClick={() => handleAddNode(nodeType.id)}
                          className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm"
                        >
                          <span className="font-medium">{nodeType.name}</span>
                          <span className="ml-2 text-xs text-gray-500">({nodeType.category})</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Selection Info */}
          {(selectedNode || selectedEdge) && (
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                {selectedNode ? (
                  <>Selected Node: <strong>{(selectedNode.data as any)?.label || selectedNode.id}</strong> ({(selectedNode.data as any)?.stepId})</>
                ) : selectedEdge ? (
                  <>Selected Edge: <strong>{selectedEdge.source}</strong> → <strong>{selectedEdge.target}</strong></>
                ) : null}
              </p>
            </div>
          )}

          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" style={{ height: "600px" }}>
            <DAGCanvas
              definition={dagDefinition}
              readonly={false}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onConnect={handleConnect}
              onNodeClick={setSelectedNode}
              onEdgeClick={setSelectedEdge}
              onPaneClick={() => { setSelectedNode(null); setSelectedEdge(null); }}
            />
          </div>
        </div>

        {/* Node Properties Panel */}
        {selectedNode && showNodePanel && (
          <div className="fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-lg overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Node Properties</h3>
                <button onClick={() => setShowNodePanel(false)} className="text-gray-500 hover:text-gray-700">✕</button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Node ID</label>
                  <input
                    type="text"
                    value={selectedNode.id}
                    disabled
                    className="w-full px-3 py-2 border rounded bg-gray-100 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Label</label>
                  <input
                    type="text"
                    value={(selectedNode.data as any)?.label || ""}
                    onChange={(e) => handleUpdateNode(selectedNode.id, {
                      data: { ...selectedNode.data, label: e.target.value }
                    })}
                    className="w-full px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Step Type</label>
                  <select
                    value={(selectedNode.data as any)?.stepId || ""}
                    onChange={(e) => handleUpdateNode(selectedNode.id, {
                      data: { ...selectedNode.data, stepId: e.target.value, stepType: e.target.value }
                    })}
                    className="w-full px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                  >
                    {NODE_TYPES.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

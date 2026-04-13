"use client";

/**
 * MITREMapping Component
 * MITRE ATT&CK 映射可视化
 */

import React from "react";
import { Shield, Target, Zap } from "lucide-react";

interface MITRETactic {
  id: string;
  name: string;
  description: string;
  techniques: MITRETechnique[];
}

interface MITRETechnique {
  id: string;
  name: string;
  description: string;
  tactics: string[];
}

interface MITREMappingProps {
  tactics: MITRETactic[];
  stage?:
    | "reconnaissance"
    | "initial_access"
    | "execution"
    | "persistence"
    | "defense_evasion"
    | "command_control"
    | "exfiltration";
}

const TACTIC_COLORS = {
  reconnaissance: {
    bg: "bg-purple-50 dark:bg-purple-900/20",
    border: "border-purple-300 dark:border-purple-700",
    text: "text-purple-700 dark:text-purple-300",
    icon: "🔍",
  },
  initial_access: {
    bg: "bg-red-50 dark:bg-red-900/20",
    border: "border-red-300 dark:border-red-700",
    text: "text-red-700 dark:text-red-300",
    icon: "🚪",
  },
  execution: {
    bg: "bg-orange-50 dark:bg-orange-900/20",
    border: "border-orange-300 dark:border-orange-700",
    text: "text-orange-700 dark:text-orange-300",
    icon: "⚡",
  },
  persistence: {
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    border: "border-yellow-300 dark:border-yellow-700",
    text: "text-yellow-700 dark:text-yellow-300",
    icon: "📌",
  },
  defense_evasion: {
    bg: "bg-pink-50 dark:bg-pink-900/20",
    border: "border-pink-300 dark:border-pink-700",
    text: "text-pink-700 dark:text-pink-300",
    icon: "🎭",
  },
  command_control: {
    bg: "bg-blue-50 dark:bg-blue-900/20",
    border: "border-blue-300 dark:border-blue-700",
    text: "text-blue-700 dark:text-blue-300",
    icon: "🎮",
  },
  exfiltration: {
    bg: "bg-green-50 dark:bg-green-900/20",
    border: "border-green-300 dark:border-green-700",
    text: "text-green-700 dark:text-green-300",
    icon: "📤",
  },
};

const KILL_CHAIN_ORDER = [
  "reconnaissance",
  "initial_access",
  "execution",
  "persistence",
  "defense_evasion",
  "command_control",
  "exfiltration",
];

export const MITREMapping = React.memo(function MITREMapping({
  tactics,
  stage,
}: MITREMappingProps) {
  if (!tactics || tactics.length === 0) {
    return (
      <div className="text-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <Target className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No MITRE ATT&CK mapping available
        </p>
      </div>
    );
  }

  // 按_kill chain 顺序排序
  const sortedTactics = [...tactics].sort((a, b) => {
    const aIndex = KILL_CHAIN_ORDER.indexOf(a.id);
    const bIndex = KILL_CHAIN_ORDER.indexOf(b.id);
    return aIndex - bIndex;
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Target className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          MITRE ATT&CK Mapping
        </h3>
      </div>

      {/* Kill Chain Visualization */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Attack Kill Chain</h4>
        </div>

        <div className="p-4">
          {/* Kill Chain Timeline */}
          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700" />

            {/* Stages */}
            <div className="flex justify-between relative">
              {KILL_CHAIN_ORDER.map((killChainStage) => {
                const hasTactics = sortedTactics.some((t) => t.id === killChainStage);
                const isCurrentStage = stage === killChainStage;
                const config = TACTIC_COLORS[killChainStage as keyof typeof TACTIC_COLORS];

                return (
                  <div key={killChainStage} className="flex flex-col items-center gap-2">
                    {/* Stage Node */}
                    <div
                      className={`
                        relative z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg
                        border-2 transition-all
                        ${
                          hasTactics
                            ? `${config.bg} ${config.border} ${config.text}`
                            : "bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-400"
                        }
                        ${
                          isCurrentStage
                            ? "ring-4 ring-offset-2 ring-blue-500 dark:ring-offset-gray-900"
                            : ""
                        }
                      `}
                      title={killChainStage.replace("_", " ")}
                    >
                      {hasTactics ? config.icon : "•"}
                    </div>

                    {/* Stage Label */}
                    <div className="text-xs text-center max-w-[80px]">
                      <div
                        className={`font-medium ${
                          hasTactics ? "text-gray-900 dark:text-white" : "text-gray-400"
                        }`}
                      >
                        {killChainStage.replace("_", " ")}
                      </div>
                      {hasTactics && (
                        <div className="text-gray-500 dark:text-gray-400">
                          {sortedTactics.find((t) => t.id === killChainStage)?.techniques.length ||
                            0}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Tactics Detail */}
      <div className="space-y-3">
        {sortedTactics.map((tactic) => {
          const config = TACTIC_COLORS[tactic.id as keyof typeof TACTIC_COLORS] || {
            bg: "bg-gray-50 dark:bg-gray-900/20",
            border: "border-gray-300 dark:border-gray-700",
            text: "text-gray-700 dark:text-gray-300",
            icon: "•",
          };

          return (
            <div
              key={tactic.id}
              className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden`}
            >
              {/* Tactic Header */}
              <div
                className={`px-4 py-3 border-b border-gray-200 dark:border-gray-700 ${config.bg}`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{config.icon}</span>
                  <div>
                    <h5 className={`font-semibold ${config.text}`}>{tactic.name}</h5>
                    {tactic.description && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                        {tactic.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Techniques */}
              {tactic.techniques && tactic.techniques.length > 0 && (
                <div className="p-4 space-y-2">
                  {tactic.techniques.map((technique, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700"
                    >
                      <Zap className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                            {technique.id}
                          </span>
                          <span className="font-medium text-sm text-gray-900 dark:text-white">
                            {technique.name}
                          </span>
                        </div>
                        {technique.description && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            {technique.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-sm text-gray-900 dark:text-white">
              Attack Analysis Summary
            </h4>
            <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Tactics:</span>
                <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                  {tactics.length}
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Techniques:</span>
                <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                  {tactics.reduce((sum, t) => sum + (t.techniques?.length || 0), 0)}
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Kill Chain Coverage:</span>
                <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                  {new Set(tactics.map((t) => t.id)).size} / {KILL_CHAIN_ORDER.length}
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Current Stage:</span>
                <span className="ml-2 font-semibold text-purple-700 dark:text-purple-300">
                  {stage ? stage.replace("_", " ") : "Unknown"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

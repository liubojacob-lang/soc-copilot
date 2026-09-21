"use client";

/**
 * MITREHeatmap Component
 * MITRE ATT&CK 战术热图 - 矩阵图
 */

import React, { useMemo } from "react";
import { Target, BarChart3 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

export interface MITRETechniqueItem {
  technique: string;
  technique_id: string;
  count: number;
}

export interface MITRETacticData {
  tactic: string;
  tactic_id: string;
  techniques: MITRETechniqueItem[];
}

export interface MITREHeatmapProps {
  data: MITRETacticData[];
  onClick?: (tactic: string, technique: string) => void;
}

interface TacticMeta {
  id: string;
  name: string;
  nameZh: string;
  color: string;
}

/**
 * 把 #rrggbb 转成 rgba(...)。
 *
 * 存在的理由是一条设计规则：**数据强度只能用"填充 alpha + 同色描边"表达，
 * 绝不能给元素加 `opacity`** —— 后者会把文字、边框一起淡掉。
 * 本组件此前正是用 `opacity: 0.35~1` 表达强度，于是白字被一起淡到 1.92:1。
 * 现在强度走 alpha，文字色固定为语义文本色，与强度解耦。
 */
function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// MITRE ATT&CK 14 项核心战术（按 Kill Chain 杀伤链顺序）
const TACTICS: Record<string, TacticMeta> = {
  reconnaissance: { id: "TA0043", name: "Reconnaissance", nameZh: "侦察", color: "#a855f7" },
  resource_development: {
    id: "TA0042",
    name: "Resource Development",
    nameZh: "资源开发",
    color: "#8b5cf6",
  },
  initial_access: { id: "TA0001", name: "Initial Access", nameZh: "初始访问", color: "#ef4444" },
  execution: { id: "TA0002", name: "Execution", nameZh: "执行", color: "#f97316" },
  persistence: { id: "TA0003", name: "Persistence", nameZh: "持久化", color: "#eab308" },
  privilege_escalation: {
    id: "TA0004",
    name: "Privilege Escalation",
    nameZh: "权限提升",
    color: "#84cc16",
  },
  defense_evasion: { id: "TA0005", name: "Defense Evasion", nameZh: "防御绕过", color: "#ec4899" },
  credential_access: {
    id: "TA0006",
    name: "Credential Access",
    nameZh: "凭据访问",
    color: "#f43f5e",
  },
  discovery: { id: "TA0007", name: "Discovery", nameZh: "发现", color: "#06b6d4" },
  lateral_movement: {
    id: "TA0008",
    name: "Lateral Movement",
    nameZh: "横向移动",
    color: "#14b8a6",
  },
  collection: { id: "TA0009", name: "Collection", nameZh: "收集", color: "#6366f1" },
  command_and_control: {
    id: "TA0011",
    name: "Command and Control",
    nameZh: "命令与控制",
    color: "#3b82f6",
  },
  exfiltration: { id: "TA0010", name: "Exfiltration", nameZh: "数据渗出", color: "#22c55e" },
  impact: { id: "TA0040", name: "Impact", nameZh: "影响", color: "#64748b" },
};

function getTacticKey(tacticName: string): string {
  return tacticName.toLowerCase().replace(/ /g, "_").replace(/-/g, "_");
}

export const MITREHeatmap = React.memo(function MITREHeatmap({ data, onClick }: MITREHeatmapProps) {
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const t = useTranslations("dashboard.mitre");

  // 转换数据格式
  const heatmapData = useMemo(() => {
    const tacticMap = new Map<string, MITRETacticData>();

    data.forEach((item) => {
      const key = getTacticKey(item.tactic);
      tacticMap.set(key, item);
    });

    return tacticMap;
  }, [data]);

  // 计算最大值用于颜色深度
  const maxCount = useMemo(() => {
    let max = 0;
    data.forEach((tactic) => {
      tactic.techniques.forEach((tech) => {
        if (tech.count > max) max = tech.count;
      });
    });
    return max;
  }, [data]);

  // 统计数据
  const totalTactics = useMemo(() => data.length, [data]);
  const totalTechniques = useMemo(
    () => data.reduce((sum, tactic) => sum + tactic.techniques.length, 0),
    [data]
  );
  const totalAlerts = useMemo(
    () =>
      data.reduce((sum, tactic) => {
        return sum + tactic.techniques.reduce((s, t) => s + t.count, 0);
      }, 0),
    [data]
  );

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center">
          <Target className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">{t("noData")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 摘要统计 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 border border-purple-200 dark:border-purple-800">
          <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
            {totalTactics}{" "}
            <span className="text-xs font-normal text-purple-700 dark:text-purple-300">/ 14</span>
          </div>
          <div className="text-xs text-purple-600 dark:text-purple-400 mt-0.5">{t("tactics")}</div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
          <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
            {totalTechniques}
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">{t("techniques")}</div>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">{totalAlerts}</div>
          <div className="text-xs text-green-600 dark:text-green-400 mt-0.5">{t("alerts")}</div>
        </div>
      </div>

      {/* MITRE ATT&CK Matrix */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-subtle">
        <div className="overflow-x-auto pb-2">
          <div className="flex gap-2 p-4 min-w-[1400px]">
            {Object.entries(TACTICS).map(([key, tactic]) => {
              const tacticData = heatmapData.get(key);
              const tacticAlertCount = tacticData
                ? tacticData.techniques.reduce((sum, t) => sum + t.count, 0)
                : 0;
              const hasData = !!tacticData && tacticData.techniques.length > 0;
              const displayName = isZh ? tactic.nameZh : tactic.name;
              const subName = isZh ? tactic.name : tactic.id;

              return (
                <div
                  key={key}
                  className="flex-1 min-w-[110px] max-w-[150px] flex flex-col rounded-lg border border-gray-100 dark:border-gray-700/60 bg-gray-50/50 dark:bg-gray-900/30 overflow-hidden"
                >
                  {/* Tactic Column Header */}
                  <div
                    className="p-2.5 text-center border-b border-gray-200/80 dark:border-gray-700/80"
                    style={{
                      borderTop: `3px solid ${tactic.color}`,
                      backgroundColor: hasData ? `${tactic.color}15` : undefined,
                    }}
                  >
                    <div
                      className="text-xs font-bold text-gray-900 dark:text-gray-100 truncate"
                      title={displayName}
                    >
                      {displayName}
                    </div>
                    <div className="text-[10px] text-text-secondary font-mono mt-0.5 truncate">
                      {subName}
                    </div>
                    <div className="mt-1">
                      {hasData ? (
                        // 计数徽章：色调只由填充承担，文字走语义色。
                        // 原先是"实色 500 级 + 白字"，实测 2.8–3.76:1，且部分色（如 #8b5cf6）
                        // 落在黑白字都无法达标的亮度死区里，靠换字色根本修不好。
                        <span
                          className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[10px] font-semibold text-text-primary"
                          style={{
                            backgroundColor: withAlpha(tactic.color, 0.16),
                            border: `1px solid ${withAlpha(tactic.color, 0.5)}`,
                          }}
                        >
                          {tacticAlertCount}
                        </span>
                      ) : (
                        <span className="text-[10px] text-text-tertiary">0</span>
                      )}
                    </div>
                  </div>

                  {/* Techniques Stack */}
                  <div className="p-1.5 flex-1 flex flex-col gap-1.5 min-h-[140px]">
                    {hasData ? (
                      tacticData.techniques.map((tech) => {
                        const intensity = maxCount > 0 ? tech.count / maxCount : 0;
                        // 强度走 alpha（0.14→0.42）。上限刻意压在 0.42：再高就会让黄/绿/青
                        // 这类亮色的填充亮度接近白字，实测 #eab308 在 0.45 时白字掉到 2.69:1。
                        const fillAlpha = 0.14 + intensity * 0.28;
                        return (
                          <div
                            key={tech.technique_id}
                            onClick={() => onClick?.(tactic.name, tech.technique)}
                            className="p-2 rounded-md border text-left cursor-pointer transition-all hover:scale-[1.02] hover:shadow-sm"
                            style={{
                              backgroundColor: withAlpha(tactic.color, fillAlpha),
                              borderColor: withAlpha(tactic.color, 0.35 + intensity * 0.4),
                            }}
                            title={`${displayName} > ${tech.technique} (${tech.technique_id}): ${tech.count} ${t("alertCount", { count: tech.count })}`}
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="text-[10px] font-mono font-bold text-text-primary tracking-wider">
                                {tech.technique_id}
                              </span>
                              <span className="px-1 py-0.2 bg-black/10 dark:bg-white/10 rounded text-[9px] font-bold text-text-primary tabular-nums">
                                ×{tech.count}
                              </span>
                            </div>
                            <div className="text-[11px] font-medium text-text-primary leading-tight line-clamp-2 mt-1">
                              {tech.technique}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="flex-1 flex items-center justify-center text-center p-2 text-[11px] text-text-tertiary border border-dashed border-border-subtle rounded">
                        {t("noActivity")}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center justify-center gap-6 text-xs text-gray-600 dark:text-gray-400 pt-1">
        <div className="flex items-center gap-2">
          <div className="w-3.5 h-3.5 bg-gray-100 dark:bg-gray-800 border border-dashed border-gray-300 dark:border-gray-600 rounded" />
          <span>{t("legendNoData")}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3.5 h-3.5 bg-blue-500 rounded" style={{ opacity: 0.35 }} />
          <span>{t("legendLow")}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3.5 h-3.5 bg-blue-500 rounded" style={{ opacity: 1 }} />
          <span>{t("legendHigh")}</span>
        </div>
      </div>

      {/* 战术详情列表 */}
      <div className="space-y-2 pt-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent-500" />
          {t("breakdown")}
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.map((tactic) => {
            const key = getTacticKey(tactic.tactic);
            const config = TACTICS[key] || {
              color: "#6b7280",
              name: tactic.tactic,
              nameZh: tactic.tactic,
              id: tactic.tactic_id,
            };
            const displayName = isZh ? config.nameZh : config.name;
            const tacticAlertCount = tactic.techniques.reduce((sum, t) => sum + t.count, 0);

            return (
              <div
                key={tactic.tactic}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3.5 shadow-subtle hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: config.color }}
                    />
                    <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                      {displayName}
                    </span>
                    <span className="text-xs text-text-tertiary font-mono">({config.id})</span>
                  </div>
                  <span className="text-xs font-medium text-accent-600 dark:text-accent-400 whitespace-nowrap">
                    {t("alertCount", { count: tacticAlertCount })}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {tactic.techniques.map((technique) => (
                    <span
                      key={technique.technique_id}
                      onClick={() => onClick?.(tactic.tactic, technique.technique)}
                      className="px-2 py-0.5 bg-surface-hover hover:bg-surface-active text-text-primary text-xs rounded border border-border-subtle transition-colors cursor-pointer inline-flex items-center gap-1"
                      title={`${technique.technique} (${technique.technique_id})`}
                    >
                      <span className="font-mono text-[10px] text-text-secondary">
                        {technique.technique_id}
                      </span>
                      <span className="truncate max-w-[120px]">{technique.technique}</span>
                      <span className="font-bold text-accent-600 dark:text-accent-400">
                        ×{technique.count}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

// 简化版：仅显示战术条形图
export function SimpleMITRETactics({
  data,
  limit = 5,
}: {
  data: MITRETacticData[];
  limit?: number;
}) {
  const sortedData = [...data]
    .sort((a, b) => {
      const aCount = a.techniques.reduce((sum, t) => sum + t.count, 0);
      const bCount = b.techniques.reduce((sum, t) => sum + t.count, 0);
      return bCount - aCount;
    })
    .slice(0, limit);

  if (sortedData.length === 0) {
    return null;
  }

  const maxCount = sortedData.reduce((max, tactic) => {
    const count = tactic.techniques.reduce((sum, t) => sum + t.count, 0);
    return Math.max(max, count);
  }, 0);

  return (
    <div className="space-y-3">
      {sortedData.map((tactic) => {
        const key = getTacticKey(tactic.tactic);
        const config = TACTICS[key] || { color: "#6b7280" };
        const count = tactic.techniques.reduce((sum, t) => sum + t.count, 0);
        const percentage = (count / maxCount) * 100;

        return (
          <div key={tactic.tactic} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-900 dark:text-white">{tactic.tactic}</span>
              <span className="text-gray-600 dark:text-gray-400">{count} alerts</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${percentage}%`,
                  backgroundColor: config.color,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

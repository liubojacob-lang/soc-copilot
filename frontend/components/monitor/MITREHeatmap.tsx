'use client';

/**
 * MITREHeatmap Component
 * MITRE ATT&CK 战术热图 - 矩阵图
 */

import React, { useMemo } from 'react';
import { Target } from 'lucide-react';

interface MITRETacticData {
  tactic: string;
  tactic_id: string;
  techniques: {
    technique: string;
    technique_id: string;
    count: number;
  }[];
}

interface MITREHeatmapProps {
  data: MITRETacticData[];
  onClick?: (tactic: string, technique: string) => void;
}

// MITRE ATT&CK 战术定义（按顺序）
const TACTICS: Record<string, { id: string; name: string; color: string }> = {
  reconnaissance: { id: 'TA0043', name: 'Reconnaissance', color: '#a855f7' },
  resource_development: { id: 'TA0042', name: 'Resource Development', color: '#8b5cf6' },
  initial_access: { id: 'TA0001', name: 'Initial Access', color: '#ef4444' },
  execution: { id: 'TA0002', name: 'Execution', color: '#f97316' },
  persistence: { id: 'TA0003', name: 'Persistence', color: '#eab308' },
  privilege_escalation: { id: 'TA0004', name: 'Privilege Escalation', color: '#84cc16' },
  defense_evasion: { id: 'TA0005', name: 'Defense Evasion', color: '#ec4899' },
  credential_access: { id: 'TA0006', name: 'Credential Access', color: '#f43f5e' },
  discovery: { id: 'TA0007', name: 'Discovery', color: '#06b6d4' },
  lateral_movement: { id: 'TA0008', name: 'Lateral Movement', color: '#14b8a6' },
  collection: { id: 'TA0009', name: 'Collection', color: '#6366f1' },
  command_and_control: { id: 'TA0011', name: 'Command and Control', color: '#3b82f6' },
  exfiltration: { id: 'TA0010', name: 'Exfiltration', color: '#22c55e' },
  impact: { id: 'TA0040', name: 'Impact', color: '#64748b' },
};

function getTacticKey(tacticName: string): string {
  const normalized = tacticName.toLowerCase().replace(/ /g, '_').replace(/-/g, '_');
  return normalized;
}

export function MITREHeatmap({ data, onClick }: MITREHeatmapProps) {
  // 转换数据格式
  const heatmapData = useMemo(() => {
    const tacticMap = new Map<string, MITRETacticData>();

    data.forEach(item => {
      const key = getTacticKey(item.tactic);
      tacticMap.set(key, item);
    });

    return tacticMap;
  }, [data]);

  // 计算最大值用于颜色深度
  const maxCount = useMemo(() => {
    let max = 0;
    data.forEach(tactic => {
      tactic.techniques.forEach(tech => {
        if (tech.count > max) max = tech.count;
      });
    });
    return max;
  }, [data]);

  // 获取单元格颜色
  const getCellColor = (count: number, tacticColor: string) => {
    if (count === 0) return '#f3f4f6'; // gray-100

    const opacity = Math.min(0.2 + (count / maxCount) * 0.8, 1);
    return tacticColor; // 使用战术颜色，透明度通过 CSS 设置
  };

  const getOpacity = (count: number) => {
    if (count === 0) return 0.3;
    return Math.min(0.2 + (count / maxCount) * 0.8, 1);
  };

  // 计算总数
  const totalTactics = useMemo(() => {
    return data.length;
  }, [data]);

  const totalTechniques = useMemo(() => {
    return data.reduce((sum, tactic) => sum + tactic.techniques.length, 0);
  }, [data]);

  const totalAlerts = useMemo(() => {
    return data.reduce((sum, tactic) => {
      return sum + tactic.techniques.reduce((s, t) => s + t.count, 0);
    }, 0);
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center">
          <Target className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No MITRE ATT&CK data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 摘要统计 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 border border-purple-200 dark:border-purple-800">
          <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">{totalTactics}</div>
          <div className="text-xs text-purple-600 dark:text-purple-400">Tactics</div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
          <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">{totalTechniques}</div>
          <div className="text-xs text-blue-600 dark:text-blue-400">Techniques</div>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">{totalAlerts}</div>
          <div className="text-xs text-green-600 dark:text-green-400">Alerts</div>
        </div>
      </div>

      {/* 热图矩阵 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <div className="min-w-[800px] p-4">
          {/* 列标题（战术） */}
          <div className="flex mb-2">
            <div className="w-24 flex-shrink-0" />
            {Object.entries(TACTICS).map(([key, tactic]) => {
              const tacticData = heatmapData.get(key);
              const hasData = !!tacticData;

              return (
                <div
                  key={key}
                  className="flex-1 min-w-[60px] text-center px-1 py-2"
                  style={{
                    backgroundColor: hasData ? tactic.color : '#f3f4f6',
                    opacity: hasData ? 1 : 0.3,
                  }}
                >
                  <div className="text-[10px] font-bold text-white leading-tight">
                    {tactic.name.split(' ')[0]}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 技巧行（简化版：仅显示数量） */}
          <div className="space-y-1">
            {Object.entries(TACTICS).map(([tacticKey, tactic]) => {
              const tacticData = heatmapData.get(tacticKey);

              return (
                <div key={tacticKey} className="flex items-center">
                  {/* 战术名称 */}
                  <div className="w-24 flex-shrink-0 pr-2 text-xs font-medium text-gray-700 dark:text-gray-300 truncate">
                    {tactic.name}
                  </div>

                  {/* 单元格 */}
                  <div className="flex-1 flex">
                    {tacticData?.techniques.map((technique) => {
                      const color = getCellColor(technique.count, tactic.color);
                      const opacity = getOpacity(technique.count);

                      return (
                        <div
                          key={technique.technique_id}
                          className="flex-1 min-w-[60px] h-8 mx-px rounded flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all"
                          style={{
                            backgroundColor: color,
                            opacity,
                          }}
                          onClick={() => onClick?.(tactic.name, technique.technique)}
                          title={`${tactic.name} > ${technique.technique}: ${technique.count} alerts`}
                        >
                          <span className="text-xs font-semibold text-white">
                            {technique.count > 0 ? technique.count : ''}
                          </span>
                        </div>
                      );
                    }) || (
                      <div className="flex-1 h-8 bg-gray-100 dark:bg-gray-700 rounded" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center justify-center gap-4 text-xs text-gray-600 dark:text-gray-400">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
          <span>No data</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rounded" style={{ opacity: 0.3 }} />
          <span>Low activity</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rounded" style={{ opacity: 1 }} />
          <span>High activity</span>
        </div>
      </div>

      {/* 战术详情列表 */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Tactics Breakdown</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {data.map((tactic) => {
            const key = getTacticKey(tactic.tactic);
            const config = TACTICS[key] || { color: '#6b7280' };

            return (
              <div
                key={tactic.tactic}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: config.color }}
                    />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {tactic.tactic}
                    </span>
                  </div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {tactic.techniques.length} technique{tactic.techniques.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {tactic.techniques.slice(0, 5).map((technique) => (
                    <span
                      key={technique.technique_id}
                      className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                    >
                      {technique.technique} ({technique.count})
                    </span>
                  ))}
                  {tactic.techniques.length > 5 && (
                    <span className="px-2 py-0.5 text-gray-500 dark:text-gray-400 text-xs">
                      +{tactic.techniques.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// 简化版：仅显示战术条形图
export function SimpleMITRETactics({ data, limit = 5 }: { data: MITRETacticData[]; limit?: number }) {
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
        const config = TACTICS[key] || { color: '#6b7280' };
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

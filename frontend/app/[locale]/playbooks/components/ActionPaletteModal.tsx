"use client";

import React, { useState, useMemo } from "react";
import { useLocale } from "next-intl";
import {
  X,
  Search,
  Shield,
  GitBranch,
  Globe,
  Database,
  Sliders,
  Sparkles,
  Plus,
} from "lucide-react";
import { ACTION_TYPE_META } from "../constants";

interface ActionPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAction: (type: string, name: string) => void;
}

const CATEGORY_META = {
  intel: {
    nameZh: "威胁情报",
    nameEn: "Threat Intelligence",
    icon: Shield,
    badge: "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20",
  },
  decision: {
    nameZh: "逻辑控制",
    nameEn: "Control Flow",
    icon: GitBranch,
    badge: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  },
  action: {
    nameZh: "响应动作",
    nameEn: "Automated Actions",
    icon: Globe,
    badge: "bg-accent-500/10 text-accent-700 dark:text-accent-300 border-accent-500/20",
  },
  data: {
    nameZh: "数据处理",
    nameEn: "Data Processing",
    icon: Database,
    badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  },
};

export function ActionPaletteModal({
  isOpen,
  onClose,
  onSelectAction,
}: ActionPaletteModalProps) {
  const locale = useLocale();
  const isZh = locale !== "en";
  const [query, setQuery] = useState("");

  const filteredActions = useMemo(() => {
    const list = Object.values(ACTION_TYPE_META);
    if (!query.trim()) return list;
    const q = query.toLowerCase();
    return list.filter(
      (a) =>
        a.nameZh.toLowerCase().includes(q) ||
        a.nameEn.toLowerCase().includes(q) ||
        a.type.toLowerCase().includes(q) ||
        a.descriptionZh.toLowerCase().includes(q) ||
        a.descriptionEn.toLowerCase().includes(q)
    );
  }, [query]);

  // Group by category
  const grouped = useMemo(() => {
    const map: Record<string, typeof filteredActions> = {
      intel: [],
      decision: [],
      action: [],
      data: [],
    };
    filteredActions.forEach((item) => {
      if (!map[item.category]) map[item.category] = [];
      map[item.category].push(item);
    });
    return map;
  }, [filteredActions]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={isZh ? "添加动作节点" : "Add Action Step"}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fade-in"
    >
      <div className="w-full max-w-2xl bg-surface-card border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between bg-surface-ground/50">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-accent-500/15 text-accent-700 dark:text-accent-300 flex items-center justify-center">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                {isZh ? "选择要添加的动作节点" : "Select Step Action to Add"}
              </h2>
              <p className="text-[11px] text-text-tertiary">
                {isZh
                  ? "选择预设的安全自动化动作，自动插入至当前 DAG 工作流拓扑中"
                  : "Pick a predefined security automation action to insert into DAG"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search input */}
        <div className="p-3 border-b border-border-subtle bg-surface-ground/30">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-text-tertiary absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={isZh ? "搜索动作类型或关键词（如: 封禁、OTX、决策、审批）..." : "Search action types..."}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-border-default bg-surface-card text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-500"
              autoFocus
            />
          </div>
        </div>

        {/* Action Grid Grouped */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {(["intel", "decision", "action", "data"] as const).map((catKey) => {
            const items = grouped[catKey] || [];
            if (items.length === 0) return null;
            const cat = CATEGORY_META[catKey];
            const CatIcon = cat.icon;

            return (
              <div key={catKey} className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
                  <CatIcon className="w-3.5 h-3.5 text-text-tertiary" />
                  <span>{isZh ? cat.nameZh : cat.nameEn}</span>
                  <span className="text-[10px] text-text-tertiary font-normal">
                    ({items.length})
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {items.map((action) => (
                    <button
                      key={action.type}
                      type="button"
                      onClick={() => {
                        onSelectAction(action.type, isZh ? action.nameZh : action.nameEn);
                        onClose();
                      }}
                      className="p-3 rounded-xl border border-border-subtle bg-surface-ground hover:bg-surface-hover hover:border-accent-500/40 text-left transition-all duration-150 flex flex-col justify-between group focus:outline-none focus:ring-2 focus:ring-accent-500/30"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-text-primary group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
                            {isZh ? action.nameZh : action.nameEn}
                          </span>
                          <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-md border ${cat.badge}`}>
                            {action.type}
                          </span>
                        </div>
                        <p className="text-[11px] text-text-tertiary line-clamp-2 leading-relaxed">
                          {isZh ? action.descriptionZh : action.descriptionEn}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}

          {filteredActions.length === 0 && (
            <div className="py-12 text-center text-text-tertiary text-xs">
              {isZh ? "未找到匹配的安全自动化动作" : "No matching actions found"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ActionPaletteModal;

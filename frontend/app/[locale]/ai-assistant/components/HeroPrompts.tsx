"use client";

import React from "react";
import { ShieldAlert, Terminal, FileCheck2, Cpu, Sparkles, ArrowUpRight } from "lucide-react";

interface HeroPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPT_SCENARIOS = [
  {
    icon: ShieldAlert,
    title: "高危网络告警排查",
    desc: "针对异常外部连接与暴力破解提供处置建议",
    prompt:
      "发现内网主机向可疑外部IP发生高频异常连接，请帮我分析潜在威胁等级，并给出阻断与排查排障建议。",
    tag: "告警研判",
    color:
      "from-rose-500/10 to-orange-500/10 hover:border-rose-500/30 text-rose-600 dark:text-rose-400",
    badgeColor: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  },
  {
    icon: Terminal,
    title: "混淆命令与代码逆向",
    desc: "反编译还原 PowerShell、Bash 或 Base64 载荷",
    prompt:
      "请帮我分析这段可疑的命令载荷，还原其真实执行意图并提取潜在的恶意域名/C2地址：powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA...",
    tag: "反混淆分析",
    color:
      "from-blue-500/10 to-cyan-500/10 hover:border-blue-500/30 text-blue-600 dark:text-blue-400",
    badgeColor: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  },
  {
    icon: FileCheck2,
    title: "ATT&CK 攻击链与报告",
    desc: "对标 MITRE 矩阵梳理横向移动并生成事件报告",
    prompt:
      "根据近期勒索攻击相关的告警日志，按 MITRE ATT&CK 战术阶段梳理攻击链拓扑，并撰写标准应急响应总结报告。",
    tag: "攻击链推演",
    color:
      "from-purple-500/10 to-indigo-500/10 hover:border-purple-500/30 text-purple-600 dark:text-purple-400",
    badgeColor: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  },
  {
    icon: Cpu,
    title: "应急响应自动化剧本",
    desc: "针对 SQL 注入或 WebShell 推荐防御编排",
    prompt:
      "针对大量探测的 SQL 注入攻击行为，推荐自动化事件响应剧本（Playbook），包括防火墙封禁、WAF联动与通知流程。",
    tag: "安全剧本",
    color:
      "from-emerald-500/10 to-teal-500/10 hover:border-emerald-500/30 text-emerald-600 dark:text-emerald-400",
    badgeColor: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
  },
];

export function HeroPrompts({ onSelectPrompt, disabled }: HeroPromptsProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center max-w-4xl mx-auto px-4 py-8 animate-fadeIn">
      {/* Hero Header */}
      <div className="text-center mb-8 space-y-3">
        <div className="inline-flex items-center justify-center p-3.5 bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 rounded-2xl shadow-xl shadow-indigo-500/20 ring-4 ring-indigo-500/10">
          <Sparkles className="w-7 h-7 text-white animate-pulse" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-gray-900 via-indigo-950 to-gray-900 dark:from-white dark:via-gray-100 dark:to-gray-300 bg-clip-text text-transparent">
          SOC Copilot · 智能安全分析助手
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xl mx-auto leading-relaxed">
          已就绪{" "}
          <span className="text-purple-600 dark:text-purple-400 font-medium">
            ⚡ 动态智能自动分配
          </span>{" "}
          · 毫秒级极速响应 · 200K 超长日志深度推理
        </p>
      </div>

      {/* Scenario Cards Grid (2x2) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full">
        {PROMPT_SCENARIOS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className={`group text-left p-4 rounded-xl border border-gray-200/70 dark:border-gray-800 bg-white/70 dark:bg-gray-900/60 backdrop-blur-md hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5 bg-gradient-to-br ${item.color} disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-white/80 dark:bg-gray-800/80 shadow-sm">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${item.badgeColor}`}
                  >
                    {item.tag}
                  </span>
                </div>
                <ArrowUpRight className="w-4 h-4 text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
              </div>
              <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {item.title}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 leading-relaxed">
                {item.desc}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

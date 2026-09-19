"use client";

import React from "react";
import { ShieldAlert, Terminal, FileCheck2, Cpu, Sparkles, ArrowUpRight } from "lucide-react";
import { useLocale } from "next-intl";

interface HeroPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPT_SCENARIOS_ZH = [
  {
    icon: ShieldAlert,
    title: "高危网络告警排查",
    desc: "针对异常外部连接与暴力破解提供处置建议",
    prompt:
      "发现内网主机向可疑外部IP发生高频异常连接，请帮我分析潜在威胁等级，并给出阻断与排查排障建议。",
    tag: "告警研判",
    color:
      "from-rose-500/10 to-orange-500/10 hover:border-rose-500/30 text-rose-700 dark:text-rose-400",
    badgeColor: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20",
  },
  {
    icon: Terminal,
    title: "混淆命令与代码逆向",
    desc: "反编译还原 PowerShell、Bash 或 Base64 载荷",
    prompt:
      "请帮我分析这段可疑的命令载荷，还原其真实执行意图并提取潜在的恶意域名/C2地址：powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA...",
    tag: "反混淆分析",
    color:
      "from-blue-500/10 to-cyan-500/10 hover:border-blue-500/30 text-blue-700 dark:text-blue-400",
    badgeColor: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
  },
  {
    icon: FileCheck2,
    title: "ATT&CK 攻击链与报告",
    desc: "对标 MITRE 矩阵梳理横向移动并生成事件报告",
    prompt:
      "根据近期勒索攻击相关的告警日志，按 MITRE ATT&CK 战术阶段梳理攻击链拓扑，并撰写标准应急响应总结报告。",
    tag: "攻击链推演",
    color:
      "from-purple-500/10 to-indigo-500/10 hover:border-purple-500/30 text-purple-700 dark:text-purple-400",
    badgeColor: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20",
  },
  {
    icon: Cpu,
    title: "应急响应自动化剧本",
    desc: "针对 SQL 注入或 WebShell 推荐防御编排",
    prompt:
      "针对大量探测的 SQL 注入攻击行为，推荐自动化事件响应剧本（Playbook），包括防火墙封禁、WAF联动与通知流程。",
    tag: "安全剧本",
    color:
      "from-emerald-500/10 to-teal-500/10 hover:border-emerald-500/30 text-emerald-700 dark:text-emerald-400",
    badgeColor: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
];

const PROMPT_SCENARIOS_EN = [
  {
    icon: ShieldAlert,
    title: "Critical Network Alert Triage",
    desc: "Analyze abnormal outbound connections and brute-force attempts",
    prompt:
      "High-frequency abnormal outbound connections to suspicious external IP detected. Please analyze threat level and provide containment recommendations.",
    tag: "Alert Triage",
    color:
      "from-rose-500/10 to-orange-500/10 hover:border-rose-500/30 text-rose-700 dark:text-rose-400",
    badgeColor: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20",
  },
  {
    icon: Terminal,
    title: "Deobfuscation & Payload Analysis",
    desc: "Decompile and decode PowerShell, Bash, or Base64 payloads",
    prompt:
      "Please analyze this suspicious command payload, reverse its execution intent and extract potential malicious C2/domains: powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA...",
    tag: "Reverse Analysis",
    color:
      "from-blue-500/10 to-cyan-500/10 hover:border-blue-500/30 text-blue-700 dark:text-blue-400",
    badgeColor: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
  },
  {
    icon: FileCheck2,
    title: "ATT&CK Chain & Incident Report",
    desc: "Map lateral movement to MITRE matrix and generate incident report",
    prompt:
      "Based on recent ransomware alert logs, map the attack chain to MITRE ATT&CK tactics and generate a standard incident response report.",
    tag: "Attack Chain",
    color:
      "from-purple-500/10 to-indigo-500/10 hover:border-purple-500/30 text-purple-700 dark:text-purple-400",
    badgeColor: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20",
  },
  {
    icon: Cpu,
    title: "Automated Incident Playbook",
    desc: "Recommend SOAR defensive playbooks for SQLi or WebShell attacks",
    prompt:
      "For widespread SQL injection attacks, recommend an automated incident response playbook including firewall blocking, WAF sync, and alerting.",
    tag: "SOAR Playbook",
    color:
      "from-emerald-500/10 to-teal-500/10 hover:border-emerald-500/30 text-emerald-700 dark:text-emerald-400",
    badgeColor: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
];

export function HeroPrompts({ onSelectPrompt, disabled }: HeroPromptsProps) {
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const scenarios = isZh ? PROMPT_SCENARIOS_ZH : PROMPT_SCENARIOS_EN;
  return (
    <div className="flex-1 flex flex-col items-center justify-center max-w-4xl mx-auto px-4 py-8 animate-fadeIn">
      {/* Hero Header */}
      <div className="text-center mb-8 space-y-3">
        <div className="inline-flex items-center justify-center p-3.5 bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 rounded-2xl shadow-xl shadow-indigo-500/20 ring-4 ring-indigo-500/10">
          <Sparkles className="w-7 h-7 text-white animate-pulse" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-primary">
          {isZh ? "SOC Copilot · 智能安全分析助手" : "SOC Copilot · AI Security Analyst"}
        </h1>
        <p className="text-sm text-text-secondary max-w-xl mx-auto leading-relaxed">
          {isZh ? "已就绪 " : "Ready "}
          <span className="text-ai-fg font-medium">
            {isZh ? "⚡ 动态智能自动分配" : "⚡ Dynamic Smart Routing"}
          </span>{" "}
          {isZh
            ? "· 毫秒级极速响应 · 200K 超长日志深度推理"
            : "· Sub-second Response · 200K Long-Context Reasoning"}
        </p>
      </div>

      {/* Scenario Cards Grid (2x2) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full">
        {scenarios.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className={`group text-left p-4 rounded-xl border border-border-subtle bg-surface-card hover:shadow-lg hover:border-border-default transition-all duration-200 hover:-translate-y-0.5 bg-gradient-to-br ${item.color} disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-surface-ground border border-border-subtle shadow-sm">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${item.badgeColor}`}
                  >
                    {item.tag}
                  </span>
                </div>
                <ArrowUpRight className="w-4 h-4 text-text-muted group-hover:text-text-primary group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
              </div>
              <h3 className="font-semibold text-sm text-text-primary mb-1 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
                {item.title}
              </h3>
              <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">
                {item.desc}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

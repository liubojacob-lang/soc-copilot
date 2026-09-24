import { ShieldAlert, MailWarning, Laptop, Sparkles } from "lucide-react";
import type { DagNodeDef, DagEdgeDef } from "../constants";

export interface TemplateOption {
  id: string;
  name: string;
  description: string;
  icon: typeof ShieldAlert;
  nodes: DagNodeDef[];
  edges: DagEdgeDef[];
}

export const TEMPLATES: TemplateOption[] = [
  {
    id: "ip-block",
    name: "恶意 IP 自动封禁",
    description: "检测高危外联告警，经威胁情报研判后自动在防火墙下发阻断规则并通知值班员",
    icon: ShieldAlert,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "alert_ingest",
        name: "告警数据解析 (Parse Alert)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "ti_lookup_otx",
        step_id: "enrich_ti",
        name: "威胁情报研判 (TI Lookup)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "decision",
        step_id: "firewall_decision",
        name: "高危判定决策 (Severity Decision)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "http_request",
        step_id: "firewall_block",
        name: "防火墙下发封禁 (Block IP via API)",
        position_x: 840,
        position_y: 80,
      },
      {
        id: "node-5",
        type: "slack_notify",
        step_id: "analyst_notify",
        name: "协同告警通知 (Slack / Email)",
        position_x: 840,
        position_y: 240,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4", condition: "threat_score >= 80" },
      { source: "node-4", target: "node-5" },
    ],
  },
  {
    id: "phishing-remediation",
    name: "钓鱼邮件快速处置",
    description: "提取邮件正文与附件 IOC，自动化沙箱引申检测，若发现恶意则全网隔离并重置凭证",
    icon: MailWarning,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "mail_alert",
        name: "邮件告警接入解析 (Parse Email)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "extract_iocs",
        step_id: "extract_iocs",
        name: "提取附件与链接 (Extract IOCs)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "ti_lookup_otx",
        step_id: "sandbox_scan",
        name: "IOC 沙箱威胁分析 (TI Lookup)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "decision",
        step_id: "verdict_eval",
        name: "恶意邮件研判决策 (Decision)",
        position_x: 840,
        position_y: 160,
      },
      {
        id: "node-5",
        type: "http_request",
        step_id: "purge_mailbox",
        name: "全网邮件撤回与封禁 (Purge Mailbox)",
        position_x: 1100,
        position_y: 80,
      },
      {
        id: "node-6",
        type: "generate_report",
        step_id: "gen_report",
        name: "生成处置复盘报告 (Generate Report)",
        position_x: 1100,
        position_y: 240,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4" },
      { source: "node-4", target: "node-5", condition: "is_malicious == true" },
      { source: "node-5", target: "node-6" },
    ],
  },
  {
    id: "endpoint-containment",
    name: "终端进程应急隔离",
    description: "EDR 捕获异常进程提权，溯源进程链，经审批节点后执行终端逻辑隔离与进程查杀",
    icon: Laptop,
    nodes: [
      {
        id: "node-1",
        type: "parse_json",
        step_id: "edr_alert",
        name: "EDR 异常注入告警 (EDR Alert)",
        position_x: 60,
        position_y: 160,
      },
      {
        id: "node-2",
        type: "timeline_build",
        step_id: "timeline_query",
        name: "溯源进程树时间线 (Timeline Build)",
        position_x: 320,
        position_y: 160,
      },
      {
        id: "node-3",
        type: "risk_score",
        step_id: "risk_eval",
        name: "危害等级风险评分 (Risk Score)",
        position_x: 580,
        position_y: 160,
      },
      {
        id: "node-4",
        type: "human_approval",
        step_id: "analyst_approval",
        name: "值班分析员人工审批 (Approval)",
        position_x: 840,
        position_y: 160,
      },
      {
        id: "node-5",
        type: "http_request",
        step_id: "isolate_host",
        name: "下发主机网络隔离 (Isolate API)",
        position_x: 1100,
        position_y: 160,
      },
    ],
    edges: [
      { source: "node-1", target: "node-2" },
      { source: "node-2", target: "node-3" },
      { source: "node-3", target: "node-4" },
      { source: "node-4", target: "node-5", condition: "approved == true" },
    ],
  },
  {
    id: "custom-blank",
    name: "自定义空白工作流",
    description: "从基础的三节点模板开始构建，自由编排输入输出、条件路由与处置动作",
    icon: Sparkles,
    nodes: [
      {
        id: "node-start",
        type: "parse_json",
        step_id: "start",
        name: "工作流输入解析 (Parse JSON)",
        position_x: 100,
        position_y: 160,
      },
      {
        id: "node-action",
        type: "decision",
        step_id: "decision",
        name: "规则研判决策 (Decision)",
        position_x: 420,
        position_y: 160,
      },
      {
        id: "node-end",
        type: "generate_report",
        step_id: "end",
        name: "响应归档报告 (Generate Report)",
        position_x: 740,
        position_y: 160,
      },
    ],
    edges: [
      { source: "node-start", target: "node-action" },
      { source: "node-action", target: "node-end" },
    ],
  },
];

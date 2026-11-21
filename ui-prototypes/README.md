# SOC Copilot (Sentinel) - 全系统高保真 UI 原型规范集

本项目目录收录了由 **Open Design** 结合产品架构规范深度设计并生成的 **SOC Copilot (Sentinel)** 全套企业级 UI 原型。

---

## 快速预览方式

直接在浏览器中打开 **`ui-prototypes/index.html`**，即可体验统一的深色原型工作台与即时多模块切换预览，支持单页全屏独立放大演示。

```bash
# 本地预览快捷方式 (Mac)
open ui-prototypes/index.html
```

---

## 模块原型清单

| 编号 | 文件名 | 对应平台路由 | 核心设计亮点 |
| :--- | :--- | :--- | :--- |
| **01** | [`01-security-cockpit.html`](./01-security-cockpit.html) | `/`, `/monitor` | **态势感知与运营中枢**：DEFCON 全局威胁状态、MTTD/MTTR 走势、攻击源流量拓扑流、MITRE ATT&CK 杀伤链热力图、右侧常驻展开的 AI Copilot 副驾驶。 |
| **02** | [`02-alert-triage-workbench.html`](./02-alert-triage-workbench.html) | `/alerts`, `/alerts/[id]` | **告警研判工作台**：多维条件筛选过滤栏、左侧告警紧凑队列、右侧研判详情抽屉、IOC 威胁证据链、Mimikatz 进程调用树图谱、原始 Wazuh 日志。 |
| **03** | [`03-soar-playbook-canvas.html`](./03-soar-playbook-canvas.html) | `/playbooks/[id]` | **SOAR 可视化剧本编排引擎**：类似 React Flow 的网格点阵画布、拖拽节点面板、贝塞尔连线与粒子仿真流动动效、右侧 Inspector 参数绑定与 JSON 预览。 |
| **04** | [`04-case-management.html`](./04-case-management.html) | `/cases`, `/cases/[id]` | **案件工单与事件协同**：事件处置全生命周期阶段流（检测 $\rightarrow$ 调查 $\rightarrow$ 遏制 $\rightarrow$ 恢复 $\rightarrow$ 结单）、时序调查时间线、数字证据保险箱、协同讨论。 |
| **05** | [`05-threat-intel-dashboard.html`](./05-threat-intel-dashboard.html) | `/threat-intel` | **威胁情报与溯源图谱**：IOC 跨源智能检索、流行 APT 组织追踪画像（APT29/Lazarus）、力导向攻击关系拓扑图谱、ATT&CK 矩阵视图。 |
| **06** | [`06-assets-ueba.html`](./06-assets-ueba.html) | `/assets`, `/ueba` | **资产管理与 UEBA 实体基线**：全网 3,420 台资产清单台账、CVE 漏洞暴露面、特权实体账号（svc_backup）行为异常偏离雷达、一键锁定与隔离。 |
| **07** | [`07-admin-audit-settings.html`](./07-admin-audit-settings.html) | `/admin/*`, `/settings/*` | **系统管理与安全审计**：48 组探针及后端服务健康监控网格、操作审计日志虚拟滚动表格、AI 大模型接入卡片（Claude 3.7 / GPT-4o / Local SecLLM）。 |

---

## 全局设计系统规范 (Design System Tokens)

- **设计美学基调**：Dark Mode First（网络安全/工业级国防指挥中心质感）
- **基底背景色**：Obsidian `#080C14` / `#0D131F`
- **卡片/面板色**：`#131B2E` / `#1A243B`（带 12px~16px 高斯模糊半透明毛玻璃）
- **边框与阴影**：`border-slate-800/80`，带微弱科技蓝背光微边
- **威胁严重度色梯**：
  - `Critical`（致命）：`#EF4444`（带呼吸光环指示）
  - `High`（高危）：`#F97316`
  - `Medium`（中危）：`#F59E0B`
  - `Low`（低危）：`#06B6D4`
  - `Safe`（正常/已恢复）：`#10B981`
- **排版字体**：
  - 界面主体：`Inter` / `Geist` / `-apple-system`
  - 数字/哈希/IP/日志：`JetBrains Mono` / `ui-monospace`

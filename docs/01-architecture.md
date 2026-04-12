# 🏗️ 架构总览

<div align="center">

![Architecture](https://img.shields.io/badge/doc-architecture-blue?style=for-the-badge&logo=diagram)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js-green?style=for-the-badge)

**理解 SOC Copilot 的整体架构设计、数据流、模块划分**

</div>

---

## 📋 目录

- [适用对象](#-适用对象)
- [系统架构](#-系统架构)
- [数据流](#-数据流)
- [后端模块](#-后端模块)
- [前端模块](#-前端模块)
- [技术栈](#-技术栈)

---

## 👥 适用对象

> [!NOTE]
> 👨‍💼 **架构师**、👨‍💻 **开发人员**、以及需要理解系统设计的工程师。

---

## 🎯 目标

理解 SOC Copilot 的整体架构设计、数据流、模块划分。

---

## 🏛️ 系统架构

```mermaid
graph TB
    subgraph 用户层
        A[🧑‍💻 用户浏览器]
    end

    subgraph 前端层[🎨 前端层 - Next.js :3003]
        B1[⚛️ React 组件]
        B2[🔄 React Flow<br/>DAG 编辑器]
        B3[📡 API Client]
        B4[🎨 Tailwind UI]
    end

    subgraph 后端层[⚙️ 后端层 - FastAPI :8000]
        C1[🔐 Authentication<br/>JWT / API Key]
        C2[🤖 AI Service<br/>NVIDIA / OpenAI]
        C3[🛡️ Alert Analyzer<br/>Timeline / Report]
        C4[⚙️ Playbook Engine<br/>DAG / Queue / Executor]
        C5[🌐 Threat Intel<br/>AlienVault OTX]
    end

    subgraph 数据层[💾 数据层]
        D1[(🗄️ SQLite<br/>app.db)]
        D2[(📊 PostgreSQL<br/>Production)]
    end

    A -->|HTTP| B1
    B1 -->|REST API| C1
    B2 -->|REST API| C4
    C1 --> C2 & C3 & C4 & C5
    C2 --> D1
    C3 --> D1
    C4 --> D1
    C5 -->|OTX API| D1
```

---

## 🌊 数据流

### 1️⃣ 告警接收流程

```mermaid
sequenceDiagram
    participant SIEM as 🔍 SIEM/EDR
    participant API as 📡 API Gateway
    participant Alert as 🛡️ Alert Service
    participant DB as 💾 Database

    SIEM->>API: POST /api/alerts
    API->>Alert: Create Alert
    Alert->>DB: Store Alert
    DB-->>Alert: Alert ID
    Alert-->>API: Alert Created
    API-->>SIEM: 201 Created
```

---

### 2️⃣ 告警分析流程

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant AI as 🤖 AI Service
    participant TI as 🌐 Threat Intel
    participant Cache as ⚡ Cache

    User->>AI: Request Analysis
    AI->>AI: Extract IOCs
    AI->>TI: Query IOC Reputation
    TI->>Cache: Check Cache
    alt Cache Hit
        Cache-->>TI: Cached Result
    else Cache Miss
        TI->>TI: Query OTX API
        TI->>Cache: Store Result
    end
    TI-->>AI: Intel Results
    AI->>AI: Generate Report
    AI-->>User: Analysis Complete
```

---

### 3️⃣ 剧本执行流程

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant API as 📡 API
    participant Queue as 📋 Queue Manager
    participant Exec as ⚙️ Executor
    participant Node as 🔧 Node Runner

    User->>API: Execute Playbook
    API->>Queue: Queue Run
    Queue->>Exec: Process Run
    loop For Each Node
        Exec->>Node: Execute Node
        Node-->>Exec: Node Result
    end
    Exec-->>Queue: Run Complete
    Queue-->>API: Status Update
    API-->>User: Execution Done
```

---

## 🖥️ 后端模块

<div align="center">

| 📁 目录         | 📝 职责       | 🔑 关键文件                          |
| :-------------- | :------------ | :----------------------------------- |
| `routers/`      | API 路由入口  | `ai.py`, `alert.py`, `playbook*.py`  |
| `services/`     | 业务逻辑      | `ai_service*.py`, `playbook_engine/` |
| `repositories/` | 数据访问层    | `alert_repo.py`, `playbook_repo.py`  |
| `models/`       | ORM 模型      | `alert.py`, `playbook.py`            |
| `schemas/`      | Pydantic 模型 | API 请求/响应定义                    |
| `core/`         | 基础配置      | `config.py`, `security.py`           |

</div>

### 模块依赖关系

```mermaid
graph LR
    A[🌐 Routers] --> B[⚙️ Services]
    B --> C[💾 Repositories]
    C --> D[🗄️ Models]
    B --> E[📋 Schemas]
    A --> E
    B --> F[🔐 Core/Security]
```

---

## 💻 前端模块

<div align="center">

| 📁 目录       | 📝 职责         | 🔑 关键文件                    |
| :------------ | :-------------- | :----------------------------- |
| `app/`        | 页面路由        | `page.tsx`, `[id]/page.tsx`    |
| `components/` | 复用组件        | `Navigation.tsx`, `dag/`       |
| `lib/`        | 工具函数        | `api.ts` (API 调用封装)        |
| `hooks/`      | 自定义 Hooks    | `useAuth.ts`, `usePlaybook.ts` |
| `types/`      | TypeScript 类型 | `alert.ts`, `playbook.ts`      |

</div>

### 前端架构

```mermaid
graph TB
    subgraph 前端架构
        A[📱 Pages] --> B[🧩 Components]
        B --> C[🪝 Hooks]
        C --> D[📡 API Client]
        D --> E[🔧 Utils]
        B --> F[🎨 UI Library]
    end
```

---

## 🛠️ 技术栈

<div align="center">

### 后端技术栈

| 层级        | 技术选型                 | 版本   | 徽章                                                                                                   |
| :---------- | :----------------------- | :----- | :----------------------------------------------------------------------------------------------------- |
| 🚀 后端框架 | FastAPI                  | 0.115+ | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) |
| 🗄️ ORM      | SQLAlchemy (Async)       | 2.0+   | ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square)                        |
| 💾 数据库   | SQLite / PostgreSQL      | 3.0+   | ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)    |
| 🔐 认证     | JWT / OAuth2             | -      | ![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens)                   |
| 🤖 AI       | NVIDIA / OpenAI / Claude | -      | ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)    |
| 🌐 威胁情报 | AlienVault OTX           | -      | ![OTX](https://img.shields.io/badge/OTX-000000?style=flat-square)                                      |

### 前端技术栈

| 层级        | 技术选型         | 版本       | 徽章                                                                                                            |
| :---------- | :--------------- | :--------- | :-------------------------------------------------------------------------------------------------------------- |
| ⚛️ 前端框架 | Next.js          | 15.1       | ![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)        |
| 🎨 UI 框架  | React + Tailwind | 19.0 + 3.4 | ![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)                |
| 📊 DAG 编辑 | React Flow       | -          | ![React Flow](https://img.shields.io/badge/React%20Flow-ff0072?style=flat-square)                               |
| 📝 语言     | TypeScript       | 5.x        | ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) |
| 🎭 图标     | Lucide React     | -          | ![Lucide](https://img.shields.io/badge/Lucide-F56565?style=flat-square)                                         |

</div>

---

## 📊 系统性能指标

<div align="center">

| 指标            | 目标值    | 说明             |
| :-------------- | :-------- | :--------------- |
| ⚡ API 响应时间 | < 200ms   | P95 响应时间     |
| 🔄 并发用户     | 100+      | 同时在线用户     |
| 📈 告警处理     | 1000/小时 | 每小时处理告警数 |
| 🗄️ 数据库       | 10万+     | 支持告警记录数   |
| 🤖 AI 响应      | < 5s      | 典型分析请求     |

</div>

---

## 🚀 下一步

<div align="center">

| 📖 推荐阅读                          | 🎯 目标           |
| :----------------------------------- | :---------------- |
| [📙 API 文档](02-api-overview.md)    | 了解 API 接口详情 |
| [📕 数据库设计](03-database.md)      | 理解数据模型      |
| [📔 剧本引擎](06-playbook-engine.md) | 学习 DAG 工作流   |

</div>

---

<div align="center">

**🏗️ 架构设计决定系统的未来**

[⬆️ 返回顶部](#-架构总览)

</div>

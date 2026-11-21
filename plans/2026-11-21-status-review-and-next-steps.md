# SOC Copilot 现状评估与下一步计划

- **评估日期**：2026-11-21
- **代码基线**：`master @ e96e08c`（`v1.0.0` 之后 23 个提交）
- **评估方式**：仓库静态盘点 + 本机实测（后端 pytest / ruff / pip-audit；前端 tsc / lint / vitest / build / npm audit；Git 与环境核查）
- **未执行**：E2E（需完整仿真栈）、Lighthouse、跨浏览器真机验证 —— 原因见 §4.6

---

## 0. 结论（先看这段）

1. **产品与技术底子已经是“1.0 形态”**：47 个 API 路由、41 个页面、37 个数据模型、10 个迁移、14 个 E2E spec，前后端约 18.2 万行；v1.0.0 GA（2026-09-21）已发 tag，55% 后端覆盖率门禁、E2E CI、alert-worker、生产 compose 都已完成。
2. **但 `master` 现在不是“可发布态”**：v1.0.0 之后还有 23 个提交（安全审计 hardening + Sentinel UI 一期 + 文档/端口统一），版本号仍停在 `1.0.0`，CHANGELOG 没有对应段落，且领先 `origin/master` 15 个提交未推送。**从 master 构建的镜像会被打上 1.0.0，内容却与已发布的 v1.0.0 不同。**
3. **门禁是回红的（实测，不是推断）**：后端 `ruff` 3 个错误；前端 CJK 棘轮 `205 > 201`；生产依赖 `npm audit` 2 critical + 2 high。更严重的是 **CI 的 pip-audit 门禁读错了 JSON 字段，实际是“永远放行”**（本次 32 条 advisories 被它报成 0 条）。
4. **已知的 3 个 UX/无障碍缺陷仍在**（错误态泄露后端信息且未 i18n、列表入口用 `<button>` 而非 `<Link>`、Dialog 关闭后焦点不回到触发元素）；`/alerts/[id]` 仍未纳入对比度闸；性能 / 移动端流程 / Safari 三个维度自 9 月至今**从未验证**。
5. **本机开发环境当前不可用**：无 `venv`、无 `node_modules`、仿真栈未启动、Docker daemon 停止、GitHub SSH 未配置；此外项目对 **Windows 原生开发有 5 处硬性不适配**（详见 §8）。

> **建议：暂停新功能，先用 2–3 个工作日完成「环境可用 → 门禁转绿 → v1.1.0 发布闭环」，再启动 Sentinel 二期。** 当前继续叠加功能只会让未发布 diff 更大、回归成本更高。

---

## 1. 项目基本盘

| 维度 | 数据 |
|---|---|
| 定位 | SOC 智能分析工作台：告警研判、时间线、报告、资产、威胁情报、Case、Playbook DAG（SOAR）、UEBA、云原生安全 |
| 技术栈 | FastAPI + SQLAlchemy 2.0(async) + PostgreSQL 15 + Redis 7；Next.js 16 + React 19 + Tailwind + next-intl |
| 后端规模 | 469 个 `.py`，93,748 行；47 个 router；37 个 model；10 个 Alembic 迁移；66 个测试文件 |
| 前端规模 | 268 个 `.ts/.tsx`，88,595 行；41 个 `page.tsx`；16 个测试套件 / 131 个用例；14 个 E2E spec |
| 质量门禁 | 后端 55% 覆盖率地板；前端 tsc + i18n keys + CJK 棘轮 + design token + contrast + prettier；E2E 4 核心 spec（PR）+ 14 spec（nightly） |
| 部署 | 开发 compose / 本地仿真 compose / 生产 compose / k8s 清单 / nginx |

功能面已经覆盖 SOC 日常主链路：登录/2FA/RBAC → 告警列表/详情/AI 分诊/RCA → Case 状态机 → Playbook 编排/审批/执行 → 报告导出 → 资产/情报/狩猎/UEBA。**“有没有功能”不再是主要问题，“能不能稳定发布和验收”才是。**

---

## 2. 版本与仓库状态

### 2.1 时间线

| 日期 | 事件 |
|---|---|
| 2026-09-19 | v0.9.4（安全修复、mock 数据清除） |
| 2026-09-21 | v1.0.0 GA（CHANGELOG 记录；E2E CI、55% 覆盖率、alert-worker、prod compose） |
| 2026-09-24 | `v1.0.0` tag 实际打在 `7869725`（CI 修复提交，晚于 GA 记录 3 天） |
| 2026-09-28 | E2E CI 修复链合并（hydration / 种子顺序 / 冷编译时序） |
| 2026-09-29 ~ 10-02 | 安全审计 `audit-run1` phase 1–2f，共 9 个提交 |
| 2026-09-30 | Sentinel 设计系统一期 + 首页工作台改造（7 套高保真原型入库） |
| 2026-10-23 | 合并 `feature/ui-redesign-sentinel` 到 master；文档/端口/脚本统一 |
| 2026-11-21 | 本次评估 |

### 2.2 Git 状态

- `master` 领先 `origin/master` **15 个提交**，全部未推送。
- `v1.0.0` tag 之后 **23 个提交**（安全审计 + Sentinel 一期 + 文档）。
- 工作区仅 `.gitignore` 一处修改（新增 `._*`、`.mypy_cache/`、`.ruff_cache/`），无 stash。
- 分支：`feature/ui-redesign-sentinel`（已合入）、`fix/audit-run1`、`release/v1.0.0` 等本地分支仍在。
- **版本号一致性**：`backend/pyproject.toml`、`frontend/package.json`、根 `package.json`、`docker-compose.prod.yml` 的 `IMAGE_TAG` 默认值、README badge 全部是 `1.0.0` —— 但它们描述的已经不是 tag `v1.0.0` 的内容。
- **CHANGELOG**：最新段落仍是 `[1.0.0] - 2026-09-21`，没有 `[Unreleased]` 或 1.1 段，v1.0.0 之后的 23 个提交**没有发布记录**。

### 2.3 远程协作

- `origin` 为 `git@github.com:liubojacob-lang/soc-copilot.git`；本机 `git ls-remote` 报 `Host key verification failed` → **未配置 SSH key，无法 push / 触发 CI**。
- 仓库内没有 issue/任务清单在跟踪遗留项（历史记录显示事项跟踪为空）。

---

## 3. 已完成并值得肯定的工作

### 3.1 v1.0.0 GA（生产就绪）

- 后端测试从 671 增至 1,248，覆盖率地板 50% → **55%**（实测 55.15%）。
- E2E CI：PR 必跑 4 条核心链路（login/alert/cases/dashboard），nightly 跑全量 14 spec + a11y。
- alert-worker Redis Streams 端到端验证 + 多渠道通知。
- 生产 compose 资源限制、预构建镜像、健康检查；k8s 清单含 alert-worker / HPA / backup CronJob。

### 3.2 安全审计 run1（phase 1–2f）—— 实质性的加固

这轮审计不是“文档审计”，每个 phase 都有可复现的回归证据（commit body 里记录了 sandbox harness C/D/E）：

| Phase | 修复要点 |
|---|---|
| 1 | 多处 auth-only 端点补 `require_analyst_or_admin`；CSRF 豁免改为精确匹配；playbook cancel owner-or-admin |
| 2a | trigger apply 权限门禁；trigger CRUD 不 commit 导致“返回 200 但没落库”；Pydantic alias 500 |
| 2b | refresh token 单次使用原子 claim（Redis SET NX），并发重放由 `[200,200]` → `[200,401]` |
| 2c | playbook 网络节点 SSRF 收口：slack_notify 入口校验、重定向逐跳校验、pinned resolver 真正生效、run input 不能覆盖目标 URL |
| 2d | 2FA 绑定要求密码 step-up；已启用不可静默覆盖；管理员改密清除 TOTP |
| 2e | trigger 幂等唯一索引 + 并发去重；账号锁定原子 UPDATE；残余 any-auth 守卫；生产禁用 `/docs`；marketplace 越权读取修复 |
| 2f | playbook 密钥绑定 definition 作者；插件 registry 单例修复；ENVIRONMENT 大小写归一；AddCredentials 精确 host；审计日志脱敏；secret 预览常量掩码 |

### 3.3 Sentinel UI 一期

- 7 套高保真原型（`ui-prototypes/01..07`）覆盖 cockpit / 告警工作台 / SOAR 画布 / Case / 情报 / 资产 UEBA / 管理。
- 已落地：设计 token（深色基底、severity 五档、cyber 工具类）、首页 cockpit 遥测横幅、StatCard/严重度分布、侧边栏品牌头。
- **其余 6 个模块仍是原型，未进入代码** → 这是最大的产品增量空间，也是最大的“设计与实现漂移”风险。

### 3.4 工程质量基础设施

- 前端 6 道 lint 闸 + 运行时对比度闸（30 个静态页 + cases/playbooks 详情页运行时发现）。
- 后端 ruff / pre-commit / bandit / pip-audit / npm audit 工作流齐全（但 pip-audit 有 bug，见 §5 P0-3）。
- 文档体系完整：开发指南、CODE_WIKI、运维部署、故障排查、验收标准。

---

## 4. 本机实测结果（2026-11-21）

> 环境：Windows 11，Python 3.12.2（`py -3.12`），Node v24.22.1，npm 12.2.1，Docker 29.9.3（daemon 未启动）。
> 依赖由本次评估新建：`venv/`（uv + Python 3.12）与根 `node_modules/`（npm workspaces）。

### 4.1 后端

| 检查 | 命令 | 结果 | 判读 |
|---|---|---|---|
| 测试 | `pytest -q` | **1,144 passed / 3 skipped / 6 failed / 98 errors**（155s） | 失败全部是 `sqlite3.OperationalError: unable to open database file`；`/tmp` 在 Windows 不存在 |
| 测试（补建 `E:\tmp` 后） | 单跑 `test_db_session.py` | 5 passed | 证明上述失败是**平台路径问题**，不是代码回归 |
| 计时用例 | 单跑 `TestExecuteDagTimeout` | passed | 全量下的失败是负载下的 flake |
| 完整重跑 | `pytest --no-cov`（DB 可用） | 在 5% 处长时间停滞，已终止 | **测试对真实 DB/外部服务有隐式依赖，非完全 hermetic**；CI 稳定性风险 |
| Lint | `ruff check .` | **3 errors**：`core/http_client.py:6,7,12` F401 | v1.0 后引入，CI backend-lint 必红 |
| 迁移 | `alembic heads` | **无法运行**：`UnicodeDecodeError: 'gbk' codec` | `alembic.ini:89` 起的中文注释在中文 Windows 上被按 GBK 解码 |
| 依赖漏洞 | `pip-audit --local` | **32 条**：aiohttp 3.14.3 ×17（fix 3.14.4）、filelock 3.32.7 ×13（fix 4.2.1）、opentelemetry-api 1.44.0 ×2（fix 1.45.x） | 其中 aiohttp 17 条含 CVE-2026-111064 等 |
| 项目门禁 | `check_pip_audit.py` | **报告 0 条 High/Critical → “gate passed”** | **门禁 bug**：脚本读 `vulnerabilities`，pip-audit 2.10 输出 `vulns`（见 §5 P0-3） |

### 4.2 前端

| 检查 | 命令 | 结果 | 判读 |
|---|---|---|---|
| 安装 | `npm ci` | 首次失败（lockfile 含 67 个 `registry.npmmirror.com` 条目，npm 12 默认 `allow-remote=none`）；`--allow-remote=all` 后 **831 包成功** | 锁文件混用镜像源，换机/CI 有隐性风险 |
| 单测 | `npm test` | **131 passed（16 suites）** | 绿 |
| 类型 | `tsc --noEmit` | **通过** | 绿 |
| 格式化 | `prettier --check` | **通过** | 绿 |
| i18n keys | `check-i18n-keys.mjs` | **通过** | 绿 |
| 对比度（token） | `check-contrast.mjs` | **exit 0**（含已登记的 B 批次容忍项） | 绿 |
| CJK 棘轮 | `check-jsx-cjk.mjs` | **❌ 205 处 > 基线 201** | 新增集中在 Sentinel 首页（`48/48 探针…`、`平均处置 MTTR:`、`本日拦截率:`）与侧边栏 |
| 设计 token | `check-design-tokens.mjs` | **无法运行**：`spawnSync ...\.bin\tailwindcss ENOENT` | Windows 下无扩展名 shell shim 不能 spawn |
| 构建 | `npm run build` | **通过**（Next 16.3.5，全路由产出） | 绿；说明 lint 红不阻塞构建 |
| 生产依赖 | `npm audit --omit=dev` | **22 条：2 critical / 2 high / 17 moderate / 1 low** | critical：`next` 16.0.0–16.4.4（装 16.3.5）、`@sentry/nextjs` 10.0.0-alpha–10.76.1（装 10.43.0）；high：`sharp` <0.35.5、`source-map-js` ≤1.2.1；均有修复版本 |

### 4.3 基线对照：21ac41a 的“CJK 绿”并不成立

用临时 worktree 在 `21ac41a`（提交信息声称 “check-jsx-cjk (201 = baseline)”）跑同一脚本，结果为 **202 处 > 201**；HEAD 为 **205 处**。即：**该提交的“已验证绿”记录不可信，之后又新增 3 处**。

### 4.4 底座质量判断

- 后端单测面广（1,144 通过），但**测试环境强依赖 POSIX 路径**，换平台即大面积报错。
- 前端 131 个用例只覆盖工具函数与 13 个组件，**页面级零单测**，质量主要靠 E2E 与 lint 闸；而 E2E 本机跑不了。
- 生产构建可过，说明“代码能跑”；但依赖漏洞与 lint 红说明“不能就这么发”。

### 4.5 未验证（与 9 月评估一致，仍是最大盲区）

| 维度 | 现状 |
|---|---|
| U1 性能 | 从未测 Lighthouse / 首屏 / CLS / bundle |
| U2 移动端真实流程 | 只测过布局不溢出，没测“登录→列表→详情→操作→返回” |
| U3 `/alerts/[id]` | 未纳入对比度闸（`contrast.spec.ts` 的 `discoverIds` 只发现 cases/playbooks） |
| U4 跨浏览器 | 只测 Chromium；Safari / iOS 未验证 |
| E2E 全量 | 本机无 Postgres/Redis/Docker，未执行 |

### 4.6 环境现状

- 端口 `13000 / 18088 / 15432 / 6379 / 8088 / 3003` **全部未监听**；仿真栈未启动。
- Docker Desktop 安装存在（WSL2 `docker-desktop` 发行版 Stopped），但 daemon 未运行。
- `.env` 指向 `postgresql+asyncpg://…@127.0.0.1:15432/soc_sim_db`，即仿真库；`.env.local-sim` 的 7 个必需变量均已配置。
- 本机无 `node_modules`、无 `venv`（本次评估已补装，均在 `.gitignore` 内）。

---

## 5. 问题清单（按优先级）

### P0 — 阻塞“可发布 / 可验收”

**P0-1 `master` 处于“半发布”状态**
- 23 个提交未发版、15 个未推送；版本号/CHANGELOG 均停在 1.0.0。
- 影响：镜像版本与源码不一致、安全修复无法交付、回滚点不清晰。
- 证据：`git describe` = `v1.0.0-23-ge96e08c`；`CHANGELOG.md` 无 1.1 段。

**P0-2 质量门禁回红（CI 今天跑必然失败）**
- 后端 `ruff` 3 个 F401（`backend/core/http_client.py:6,7,12`）。
- 前端 CJK 棘轮 205 > 201（Sentinel 首页 + 侧边栏新增硬编码中文）。
- 前端 `npm audit` 2 critical（next、@sentry/nextjs）+ 2 high（sharp、source-map-js）。
- 判读：`ci-cd.yml` 的 `backend-lint` / `frontend-lint` 与 `security-gate` 的 `npm-audit` 都会红。

**P0-3 安全门禁存在“盲区”**
- `.github/scripts/check_pip_audit.py:36` 读取 `dep["vulnerabilities"]`，而 pip-audit 2.10 输出 `dep["vulns"]` → 任何漏洞都统计不到。
- 实测：32 条 advisories（含 aiohttp 17 条 CVE/GHSA）被报成 0 条并放行。
- 影响：这是**安全流水线的假绿**，比没有门禁更危险（给团队错误信心）。

**P0-4 本机环境不可复现**
- 无依赖、无仿真、Docker/SSH 未就绪；`AGENTS.md` 要求的 `./Scripts/sim.sh update` 当前无法执行。
- 影响：任何改动都无法完成“自检 + 仿真同步”的既定流程。

**P0-5 Windows 原生开发不适配（5 处）**
1. `backend/conftest.py:17` 固定 `/tmp/soc_copilot_test.db` → Windows 上不存在，98 个测试直接 error。
2. `backend/alembic.ini:89` 起中文注释 + Alembic 以 `encoding="locale"` 读取 → 中文 Windows（GBK）崩溃。
3. `backend/requirements.txt:20,69` 含 em dash，`pip-audit -r` / `pip_requirements_parser` 按 locale 解码崩溃。
4. `frontend/package.json:7` 的 `dev` 使用 `NODE_OPTIONS='...'` POSIX 前缀 → cmd/PowerShell 下不可用。
5. `package-lock.json` 混有 67 个 `registry.npmmirror.com` 绝对 URL；npm 12 默认拒绝“remote”包，必须 `--allow-remote=all`。
   （另有第 6 处：`check-design-tokens.mjs` 依赖无扩展名 `.bin/tailwindcss`，Windows 下无法 spawn。）

### P1 — 用户可见 / 发版前应修

**P1-1 v1.0 就绪度评估的 3 个阻塞项仍未修**
- B2 `/alerts/[id]` 错误态：`page.tsx:922` `error={error || "Alert not found"}` —— 硬编码英文，且把 FastAPI/Pydantic 原始错误渲染进 UI（信息泄露 + 不可读）。
- B3 列表→详情仍用 `<button onClick={router.push}>`：`alerts/page.tsx:630,780`、`cases/page.tsx:282,387`、`playbooks/page.tsx:304` —— 不能新标签打开 / 不能复制链接 / 读屏宣告为按钮。
- S1 Dialog 焦点恢复：`hooks/useFocusTrap.ts:63-75` 的恢复逻辑只在 `!isOpen` 分支，cleanup（127-130）不含恢复 → 条件渲染卸载时焦点落回 `<body>`。

**P1-2 对比度闸覆盖不全**
- `frontend/e2e/a11y/contrast.spec.ts:447` 的 `discoverIds` 只发现 cases / playbook-definitions，**没有 alerts**；P1-1 的 B2 页面恰好不在闸内。
- 9 月记录的 `/cases/[id]` 3.3:1、`/playbooks/[id]` 4.34:1 是否修掉**无复验证据**（本机无法跑 E2E）。

**P1-3 安全审计缺“收尾报告”**
- phase 1–2f 的修复细节都在 commit body 里，但仓库没有一份审计报告：范围、发现总数、已修/未修、残余风险、复测结论。
- 对外（客户/等保/ISO）无法证明“审计闭环”；对内无法判断“还剩多少”。

**P1-4 三个产品决策悬空（自 9 月至今）**
1. `escalated` 状态与“创建工单”是否拆开？
2. “升级为工单”的两个入口是否合并？
3. 硬编码色（4,569 处）是独立技术债还是并入功能迭代？

**P1-5 文档/生成物漂移**
- `.claude/CLAUDE.md` 仍写 v0.9.0、SQLite、前端 3003/后端 8000（实际 8088 + PostgreSQL）。
- `openapi.json` 最后提交于 2026-04-12，而现有 47 个 router；`frontend/types/api.generated.ts` 为 9 月生成。
- `docs/09-ops-deploy.md` 仍提“SQLite 兜底库”，与 `db/session.py` 拒绝无 `DATABASE_URL` 启动的行为不符。
- `docs/11-roadmap.md` 只到 v1.0，没有 v1.1 计划。

### P2 — 技术债 / 后续能力

- Sentinel 二期：7 个原型只落地 1 个（首页）。告警工作台、Case、SOAR 画布、情报、资产/UEBA、管理 6 个模块待实现。
- 备份与恢复演练未做（k8s 有 CronJob，但“恢复一次”无记录）；生产 compose 干净机部署演练未做。
- NVIDIA API key 轮换（用户侧动作）、Git 历史密钥 blob 清理决策未做。
- 前端 131 个单测覆盖薄；页面级逻辑主要靠 E2E。
- 后端测试非 hermetic（依赖真实 DB 的用例在无库时 error，有库时可能挂起）。
- `openapi.json` / `api.generated.ts` 过期；`FUTURE_BACKLOG` 中监控栈、审计归档对象存储、i18n 存量等仍在。

---

## 6. 下一步计划

> 原则：**先让现状可验收，再谈新功能**。每个阶段有明确 DoD，做完再进下一阶段。

### 阶段 0：环境可用（0.5–1 天）

**决策：推荐 WSL2 + Docker Desktop（Ubuntu），而不是原生 Windows。**
理由：项目脚本全部是 bash、`/tmp` 路径、Alembic locale、npm 脚本 POSIX 语法——在 WSL2 里这些都是“本来就该工作的样子”，原生 Windows 需要改 6 处代码/配置（§8），反而增加与团队其他环境的分叉。

任务：
1. 启动 Docker Desktop（WSL2 backend），确认 `docker info` 正常。
2. `./Scripts/sim.sh start` → `./Scripts/sim.sh status` → 验证：
   - 前端 `http://127.0.0.1:13000`
   - 后端 `http://127.0.0.1:18088/api/health` 与 `/api/v1/health`
3. 跑一次主链路冒烟：登录 → 告警列表 → 详情 → 建 Case → 剧本 dry-run → 报告 → 登出。
4. 配置 GitHub SSH（`ssh -T git@github.com` 通），把本地分支推到远端（先推 `release/v1.1.0` 分支，不直接推 master）。

**DoD**：仿真三服务 healthy；主链路无阻断；`git ls-remote` 可用。

### 阶段 1：门禁转绿（1–2 天）

1. **后端 lint**：删除 `core/http_client.py` 的 3 个未使用 import；`ruff check .` 归零。
2. **前端 CJK**：把 Sentinel 首页 3 处遥测文案 + 侧边栏 2 处抽到 `messages/{en,zh-CN}`；修正 `.i18n-cjk-baseline.json` 的 `count`(201) 与 `entries`(193) 不一致；`check-jsx-cjk` 回到 ≤201（只降不升）。
3. **依赖升级（安全）**：
   - `next` → ≥16.4.5，`@sentry/nextjs` → ≥10.76.2，`sharp` → ≥0.35.5，`source-map-js` → ≥1.2.2；
   - 后端 `aiohttp` → 3.14.4，`opentelemetry-*` → 1.45.x；`filelock` 属安全扫描工具链，单独评估。
   - 升级后重跑：前端 `npm test` + `npm run build` + `npm audit`；后端 `pytest`。
4. **修复 pip-audit 门禁**：`.github/scripts/check_pip_audit.py` 兼容 `vulns` 字段（保留旧字段），并加一个 fixture 回归测试；修复后应能真实报出 aiohttp 漏洞，再配合升级归零。
5. **测试可移植性**：`backend/conftest.py` 用 `tempfile.gettempdir()` 替代 `/tmp`；`requirements.txt` 的 em dash 改 ASCII；`alembic.ini` 中文注释改 ASCII 或显式 UTF-8（若坚持原生 Windows）。
6. **生成物**：重新导出 `openapi.json` 与 `api.generated.ts`，确认 `tsc` 仍过。

**DoD**：`ruff` 0；`npm run lint` 全链绿；`pytest` 全量绿（含 CI 环境）；`npm audit --omit=dev` 0 high/critical；pip-audit 门禁能真实拦截。

### 阶段 2：v1.1.0 发布闭环（1 天）

1. 从 master 切 `release/v1.1.0`（不直接在 master 提交）。
2. 版本号 5 处统一 → `1.1.0`（pyproject / frontend / root package / compose IMAGE_TAG / README）。
3. 写 `CHANGELOG [1.1.0]`：安全审计 phase 1–2f、Sentinel 一期、E2E CI 修复、端口/文档统一、依赖升级；明确“不含 SSO/K8s 多实例/多租户”。
4. 本地跑 `release.yml` 等价校验；`workflow_dispatch` dry-run 一次。
5. 合并回 master，push，打 tag `v1.1.0`，观察 release 流水线（镜像 + changelog + release notes）。

**DoD**：tag 与源码一致；release 全绿；镜像 `1.1.0` 可用；`git status` 干净。

### 阶段 3：体验与验证债（2–3 天）

1. 修 P1-1 三项：B2 错误态（i18n + 不渲染技术细节）、B3 改 `<Link>`、S1 焦点恢复移入 cleanup。
2. `contrast.spec.ts` 的 `discoverIds` 增加 alert ID；跑 a11y E2E，清零新增失败；把 9 月记录的 cases/playbooks 对比度缺陷复验并关闭。
3. 补 U1/U2/U4：
   - Lighthouse 跑首页/告警列表/详情，记录 LCP/CLS/TBT；
   - 375px 走完整流程；
   - Safari（至少桌面）跑登录 + 告警详情。
   结论写入 `docs/reports/`。
4. 写《安全审计收尾报告》：范围、发现清单（编号/级别/状态）、修复提交、残余风险与接受理由、复测命令。

**DoD**：3 个缺陷关闭；a11y E2E 绿；性能/移动端/Safari 有数据；审计报告入库。

### 阶段 4：Sentinel 二期（1–2 周，按模块迭代）

优先顺序（按日常价值）：
1. **告警研判工作台**（原型 02）：左队列 + 右详情抽屉 + IOC 证据链 —— 与现有 `/alerts` 融合，ROI 最高。
2. **Case 管理**（原型 04）：生命周期阶段流 + 时间线 + 证据箱。
3. **SOAR 画布**（原型 03）：在现有 React Flow 上做视觉升级，不动执行引擎。
4. 情报看板（05）→ 资产/UEBA（06）→ 管理/审计（07）。

每个模块的 DoD：设计 token 合规 + 双语 i18n + 对比度闸覆盖 + 至少 1 条 E2E + 截图归档。

### 阶段 5：生产化 backlog（持续）

- 备份 cron + **恢复演练一次**（写入 Makefile 与运维文档）。
- 干净机器 `docker compose -f docker-compose.prod.yml up` 演练（补 JWT_SECRET / SECRET_ENCRYPTION_KEY / CORS / DOCKERHUB_USERNAME）。
- 轮换 NVIDIA API key；决定是否做 git 历史密钥清理（仓库转公开前必做）。
- 监控栈补齐（Prometheus rules / Grafana 面板挂载 / Alertmanager）。
- 覆盖率 55% → 60%（v1.x），优先补 `auth_service` 降级路径与 `case_service` 状态机。

### 排期建议

| 阶段 | 内容 | 预估 |
|---|---|---|
| 0 | 环境可用 | 0.5–1 天 |
| 1 | 门禁转绿 | 1–2 天 |
| 2 | v1.1.0 发布 | 1 天 |
| 3 | 体验/验证债 | 2–3 天 |
| 4 | Sentinel 二期 | 1–2 周 |
| 5 | 生产化 backlog | 持续 |

**合计：约 5–7 个工作日回到“可发布、可演示、门禁可信”的状态；之后进入 Sentinel 二期。**

---

## 7. 需要你拍板的事

1. **开发环境**：WSL2（推荐）还是继续原生 Windows？（后者需要接受 §8 的 6 处修改）
2. **版本号**：v1.1.0（推荐，含 Sentinel 首页 + 安全加固）还是 v1.0.1（更保守）？
3. **Sentinel 二期首个模块**：告警研判工作台（推荐）还是 Case 管理？
4. **三个产品决策**（§5 P1-4）：`escalated` 语义、工单入口合并、硬编码色排期。
5. **发布权限**：push/tag 是否需要你确认后再执行？（当前仓库规范要求确认）

---

## 8. 附：Windows 原生环境修复清单（若不走 WSL2）

| # | 文件 | 问题 | 修法 |
|---|---|---|---|
| 1 | `backend/conftest.py:17`、`tests/conftest.py` | 固定 `/tmp/...` | `Path(tempfile.gettempdir()) / "soc_copilot_test.db"` |
| 2 | `backend/alembic.ini:89` | 中文注释 + locale 解码 | 注释改 ASCII；或在 `env.py` 用 `config.file_config.read(path, encoding="utf-8")` |
| 3 | `backend/requirements.txt:20,69` | em dash 导致 pip-audit/safety 解析崩溃 | 改 `--`（纯 ASCII） |
| 4 | `frontend/package.json:7` | `NODE_OPTIONS='...'` POSIX 语法 | 用 `cross-env` 或 `next dev` 配置 `--max-old-space-size` |
| 5 | `package-lock.json` | 67 个 npmmirror 绝对 URL | `npm config set registry https://registry.npmjs.org/` 后重生成 lock；或团队统一 `--allow-remote=all` |
| 6 | `frontend/scripts/check-design-tokens.mjs:67` | 找不到无扩展名 shim | 解析 `tailwindcss.cmd` / 用 `process.execPath` + `tailwindcss/lib/cli.js` |

> 注意：修完这些仍需 Docker Desktop（仿真）与 GitHub SSH；脚本层（`sim.sh`、`*.sh`）在原生 Windows 下需要 Git Bash，`make` 目标也不可用。这是推荐 WSL2 的核心理由。

---

## 附录 A：本次实测命令速查

```bash
# 后端
py -3.12 -m venv venv
venv/Scripts/python -m pip install -r backend/requirements.txt -r backend/requirements-test.txt
cd backend && PYTHONPATH=. ENVIRONMENT=test ../venv/Scripts/python -m pytest -q
cd backend && ../venv/Scripts/python -m ruff check .

# 前端
cd frontend && npm ci --allow-remote=all
npm test
npx tsc --noEmit
npm run build
npm run lint   # 会在 check-jsx-cjk 处失败
npm audit --omit=dev

# 安全
venv/Scripts/pip-audit --local -f json -o pip-audit.json
```

## 附录 B：关键证据位置

- 版本/发布：`CHANGELOG.md`、`backend/pyproject.toml:3`、`docker-compose.prod.yml:64,98,156`
- lint 红：`backend/core/http_client.py:6,7,12`；`frontend/scripts/check-jsx-cjk.mjs`
- 门禁盲区：`.github/scripts/check_pip_audit.py:36`
- UX 债：`frontend/app/[locale]/alerts/[id]/page.tsx:922`、`frontend/app/[locale]/alerts/page.tsx:630,780`、`frontend/hooks/useFocusTrap.ts:63`
- 对比度盲区：`frontend/e2e/a11y/contrast.spec.ts:447`
- Windows 适配：`backend/conftest.py:17`、`backend/alembic.ini:89`、`backend/requirements.txt:20,69`、`frontend/package.json:7`
- 安全审计细节：`git log a10f9aa^..e96e08c --format=%B`
</content>

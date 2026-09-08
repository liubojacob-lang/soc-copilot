# SOC Copilot 版本发布规范

> 关联需求：FR-003（版本发布流程管理）
> 前置依赖：FR-001（Git 分支策略配置）

## 1. 版本号规范

### 1.1 SemVer 语义化版本

本项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) 规范，版本号格式为：

```
MAJOR.MINOR.PATCH
```

| 版本类型 | 递增规则            | 示例           | 触发条件                 |
| -------- | ------------------- | -------------- | ------------------------ |
| MAJOR    | 不兼容的 API 变更   | 0.9.0 → 1.0.0  | 架构重构、API 破坏性变更 |
| MINOR    | 向后兼容的功能新增  | 0.9.0 → 0.10.0 | 新功能、新模块           |
| PATCH    | 向后兼容的 Bug 修复 | 0.9.0 → 0.9.1  | Bug 修复、安全补丁       |

### 1.2 版本号管理策略

#### 版本号存储位置

| 文件                     | 格式                 | 说明               |
| ------------------------ | -------------------- | ------------------ |
| `backend/pyproject.toml` | `version = "X.Y.Z"`  | 后端 Python 包版本 |
| `frontend/package.json`  | `"version": "X.Y.Z"` | 前端 NPM 包版本    |

#### 递增决策矩阵

| 变更类型               | MAJOR | MINOR | PATCH | 示例                            |
| ---------------------- | ----- | ----- | ----- | ------------------------------- |
| 删除或重命名公共 API   | ✅    |       |       | 删除 `/api/v1/alerts` 端点      |
| 修改 API 响应结构      | ✅    |       |       | 响应字段类型变更                |
| 新增 API 端点          |       | ✅    |       | 新增 `/api/v1/correlation` 端点 |
| 新增功能模块           |       | ✅    |       | 新增 Playbook DAG 引擎          |
| 新增配置项（有默认值） |       | ✅    |       | 新增环境变量 `LOG_LEVEL`        |
| Bug 修复               |       |       | ✅    | 修复告警过滤逻辑错误            |
| 安全补丁               |       |       | ✅    | 修复 XSS 漏洞                   |
| 文档更新               |       |       |       | 不触发版本递增                  |
| 代码格式化/重构        |       |       |       | 不触发版本递增                  |

#### 0.x.x 阶段特殊规则

- 在 `0.x.x` 阶段，MINOR 版本递增允许包含不兼容的 API 变更
- 进入 `1.0.0` 后，严格遵循 SemVer 规范
- 进入 `1.0.0` 的条件：API 稳定、核心功能完备、至少经过一个生产周期验证

## 2. 标准发布流程（9 步）

### 流程概览

```
步骤1: 版本号规划 ──→ 步骤2: 更新 CHANGELOG ──→ 步骤3: 代码冻结
      │                                                    │
步骤9: 发布归档 ←── 步骤8: 合并回 develop ←── 步骤7: 部署生产
      │                                                    │
步骤4: 创建 release 分支 ──→ 步骤5: CI 验证 ──→ 步骤6: 审批发布
```

### 步骤 1：版本号规划

**负责人**：项目负责人

**操作**：

1. 评估自上次发布以来的变更，确定版本递增类型（MAJOR/MINOR/PATCH）
2. 确认所有计划包含的功能已合并到 develop 分支
3. 确认无阻塞级别的未解决问题

**命令**：

```bash
make release-plan VER=x.y.z
```

### 步骤 2：更新 CHANGELOG

**负责人**：DevOps 工程师

**操作**：

1. 运行 CHANGELOG 自动生成脚本
2. 审核并补充 CHANGELOG 条目
3. 确保所有变更正确分类

**命令**：

```bash
make release-changelog VER=x.y.z
```

### 步骤 3：代码冻结

**负责人**：项目负责人

**操作**：

1. 通知团队进入代码冻结期
2. 冻结后仅允许 Bug 修复合入
3. 新功能必须推迟到下一版本

**通知模板**：

```
🔒 代码冻结通知
版本：vX.Y.Z
冻结时间：YYYY-MM-DD HH:MM
解冻条件：发布完成
期间仅允许：Bug 修复、文档更新、版本号变更
```

### 步骤 4：创建 release 分支

**负责人**：DevOps 工程师

**操作**：

1. 从 develop 创建 `release/vX.Y.Z` 分支
2. 更新版本号（pyproject.toml + package.json）
3. 提交版本号变更

**命令**：

```bash
make release-start VER=x.y.z
```

### 步骤 5：CI 全量验证

**负责人**：DevOps 工程师

**操作**：

1. CI 流水线自动运行全量检查
2. 包含：代码质量、单元测试、集成测试、安全扫描
3. 所有检查必须通过

**自动触发**：push 到 `release/*` 分支自动触发 CI

### 步骤 6：审批发布

**负责人**：项目负责人

**操作**：

1. 创建发布 PR（release 分支 → main）
2. 审核版本号、CHANGELOG、代码变更
3. 审批 PR

**模板**：`.github/PULL_REQUEST_TEMPLATE/release.md`

### 步骤 7：部署生产

**负责人**：DevOps 工程师

**操作**：

1. PR 合并后自动触发发布工作流
2. 工作流自动完成：Git Tag 创建 → GitHub Release 发布 → Docker 镜像构建推送
3. 部署到生产环境（由 FR-005 部署流程管理负责）

**自动触发**：PR 合并到 main 后自动触发 `release.yml` 工作流

### 步骤 8：合并回 develop

**负责人**：DevOps 工程师

**操作**：

1. 将 release 分支合并回 develop
2. 确保 develop 包含版本号和 CHANGELOG 更新
3. 删除 release 分支

**命令**：

```bash
make release-finish VER=x.y.z
```

### 步骤 9：发布归档

**负责人**：DevOps 工程师

**操作**：

1. 确认 GitHub Release 已创建
2. 确认 Docker 镜像已推送
3. 通知团队发布完成
4. 更新项目文档

**通知模板**：

```
🚀 发布完成通知
版本：vX.Y.Z
发布时间：YYYY-MM-DD HH:MM
Docker 镜像：ghcr.io/org/soc-copilot-backend:X.Y.Z
GitHub Release：https://github.com/org/soc-copilot/releases/tag/vX.Y.Z
```

## 3. Hotfix 发布流程

当生产环境发现紧急问题需要立即修复时，使用 Hotfix 流程：

```
步骤1: 创建 hotfix 分支（从 main）
    ↓
步骤2: 修复 Bug
    ↓
步骤3: 更新版本号（PATCH 递增）
    ↓
步骤4: 更新 CHANGELOG
    ↓
步骤5: CI 验证
    ↓
步骤6: 创建 PR → main + develop
    ↓
步骤7: 审批并合并
    ↓
步骤8: 自动发布（与标准流程步骤7相同）
```

**命令**：

```bash
# 1. 创建 hotfix 分支
make branch-create-hotfix VER=x.y.z DESC=fix-desc

# 2. 修复完成后更新版本号
make release-bump VER=x.y.z

# 3. 生成 CHANGELOG
make release-changelog VER=x.y.z

# 4. 提交并创建 PR
git add -A && git commit -m "hotfix: v$(VER)"
# 创建 PR 到 main 和 develop
```

## 4. Git Commit 规范

### 4.1 Conventional Commits

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 Type 定义

| Type     | 说明          | CHANGELOG 分类 | 版本递增影响 |
| -------- | ------------- | -------------- | ------------ |
| feat     | 新功能        | Added          | MINOR        |
| fix      | Bug 修复      | Fixed          | PATCH        |
| perf     | 性能优化      | Changed        | PATCH        |
| refactor | 代码重构      | Changed        | PATCH        |
| docs     | 文档更新      | 不计入         | 无           |
| style    | 代码格式      | 不计入         | 无           |
| test     | 测试用例      | 不计入         | 无           |
| chore    | 构建/工具变更 | 不计入         | 无           |
| ci       | CI 配置变更   | 不计入         | 无           |
| revert   | 回滚提交      | Fixed          | PATCH        |

### 4.3 Scope 定义

| Scope    | 说明          |
| -------- | ------------- |
| api      | API 路由/端点 |
| model    | 数据模型      |
| playbook | Playbook 引擎 |
| ai       | AI 功能       |
| alert    | 告警相关      |
| auth     | 认证授权      |
| ui       | 前端界面      |
| deploy   | 部署相关      |
| security | 安全相关      |
| monitor  | 监控相关      |

### 4.4 Breaking Changes

破坏性变更必须在 footer 中标注：

```
feat(api): redesign alert API response structure

BREAKING CHANGE: Alert API response fields renamed from `alert_id` to `id`
Migration guide: docs/migration/v1.0.0.md
```

## 5. 发布检查清单

### 发布前检查

- [ ] 版本号已更新（pyproject.toml + package.json）
- [ ] CHANGELOG.md 已更新
- [ ] 所有计划功能已合并
- [ ] CI 全量检查通过
- [ ] 安全扫描无高危漏洞
- [ ] 数据库迁移脚本已准备（如有）
- [ ] API 兼容性已确认
- [ ] 发布 PR 已创建并审批

### 发布后验证

- [ ] Git Tag 已创建
- [ ] GitHub Release 已发布
- [ ] Docker 镜像已推送
- [ ] 生产环境部署成功
- [ ] 健康检查通过
- [ ] release 分支已合并回 develop
- [ ] release 分支已删除
- [ ] 团队已收到发布通知

## 6. 版本生命周期

```
规划中 → 已冻结 → 已审批 → 已发布 → 已归档
                      ↓
                   已回滚
```

| 状态   | 说明                      | 允许操作             |
| ------ | ------------------------- | -------------------- |
| 规划中 | 版本号已确定，功能收集中  | 合并功能到 develop   |
| 已冻结 | 代码冻结，仅允许 Bug 修复 | Bug 修复、版本号更新 |
| 已审批 | 发布 PR 已审批            | 合并到 main          |
| 已发布 | 已部署到生产环境          | 归档、通知           |
| 已回滚 | 生产环境回滚              | 修复后重新发布       |
| 已归档 | 发布完成，记录归档        | 无                   |

## 7. 工具链参考

| 工具                       | 用途                          | 文件                                     |
| -------------------------- | ----------------------------- | ---------------------------------------- |
| `make release-plan`        | 版本规划                      | Makefile                                 |
| `make release-start`       | 创建 release 分支并更新版本号 | Makefile + scripts/bump-version.sh       |
| `make release-changelog`   | 生成 CHANGELOG                | Makefile + scripts/generate-changelog.sh |
| `make release-finish`      | 合并回 develop 并清理         | Makefile + scripts/release-branch.sh     |
| `make release-bump`        | 更新版本号                    | Makefile + scripts/bump-version.sh       |
| GitHub Actions release.yml | 自动化发布流水线              | .github/workflows/release.yml            |

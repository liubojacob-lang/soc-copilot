# SOC Copilot Git 分支策略与命名规范

> 关联需求：FR-001（分支策略管理）
> 最后更新：2025-06-22

## 1. 概述

SOC Copilot 项目采用 **Git Flow 简化变体**，适配 3-8 人小团队规模。本规范定义了分支类型、命名规则、保护策略、合并策略以及与 CI 流水线的触发对应关系。

## 2. 分支模型

```
main ──────────────────────────────────── ● ────────────── ● ──────
                                         │                 │
                              release/v0.10.0 ──┘         │
                                         │                 │
develop ───── ● ────── ● ────── ● ────── ● ────── ● ────── ● ────
              │         │         │
   feature/FR-001-alert-dedup   │
              │         │         │
              └─────────┘   fix/FR-002-login-bug
                                        │
                                        └─────────┘
```

## 3. 分支类型定义

| 分支类型    | 命名规范                  | 创建自        | 合并至       | 保护规则                                      | 生命周期   |
| ----------- | ------------------------- | ------------- | ------------ | --------------------------------------------- | ---------- |
| **main**    | `main`                    | -             | -            | 禁止直接推送、必须PR、至少1人审批、CI必须通过 | 永久       |
| **develop** | `develop`                 | main          | -            | 禁止直接推送、必须PR                          | 永久       |
| **feature** | `feature/FR-xxx-简短描述` | develop       | develop      | 无                                            | 合并后删除 |
| **fix**     | `fix/FR-xxx-简短描述`     | develop或main | 来源分支     | 无                                            | 合并后删除 |
| **release** | `release/vX.Y.Z`          | develop       | main+develop | 仅项目负责人可创建                            | 发布后删除 |
| **hotfix**  | `hotfix/vX.Y.Z-简短描述`  | main          | main+develop | 仅项目负责人可创建                            | 合并后删除 |

## 4. 分支命名规范

### 4.1 命名格式

#### Feature 分支

```
feature/FR-<编号>-<简短英文描述>
```

- **编号**：对应需求文档中的需求编号（如 FR-001）
- **描述**：使用 kebab-case，2-5 个单词，简明描述功能
- **示例**：`feature/FR-001-alert-dedup`, `feature/FR-015-env-management`

#### Fix 分支

```
fix/FR-<编号>-<简短英文描述>
```

- **编号**：对应 Bug 报告或需求编号
- **描述**：使用 kebab-case，简明描述修复内容
- **示例**：`fix/FR-002-login-timeout`, `fix/FR-010-rbac-permission`

#### Release 分支

```
release/v<主版本>.<次版本>.<修订版本>
```

- 遵循语义化版本 (SemVer)
- **示例**：`release/v0.10.0`, `release/v1.0.0`

#### Hotfix 分支

```
hotfix/v<主版本>.<次版本>.<修订版本>-<简短描述>
```

- 版本号表示修复后的目标版本
- **示例**：`hotfix/v0.10.1-xss-fix`, `hotfix/v1.0.1-auth-bypass`

### 4.2 命名规则

| 规则         | 说明                                 |
| ------------ | ------------------------------------ |
| 全部小写     | 分支名仅使用小写字母                 |
| 使用连字符   | 单词间使用 `-` 连接（kebab-case）    |
| 禁止空格     | 分支名中不允许包含空格               |
| 禁止下划线   | 使用连字符替代下划线                 |
| 需求编号必须 | feature/fix 分支必须包含 FR-xxx 编号 |
| 描述简洁     | 描述部分控制在 2-5 个单词            |

### 4.3 正则表达式验证

```bash
# feature 分支
^feature/FR-[0-9]+-[a-z][a-z0-9-]+$

# fix 分支
^fix/FR-[0-9]+-[a-z][a-z0-9-]+$

# release 分支
^release/v[0-9]+\.[0-9]+\.[0-9]+$

# hotfix 分支
^hotfix/v[0-9]+\.[0-9]+\.[0-9]+-[a-z][a-z0-9-]+$

# 永久分支
^(main|develop)$
```

## 5. 分支保护规则

### 5.1 main 分支保护规则

| 规则                | 设置 | 说明                     |
| ------------------- | ---- | ------------------------ |
| 禁止直接推送        | ✅   | 所有变更必须通过 PR      |
| 必须通过 PR         | ✅   | 不允许直推               |
| 最低审批人数        | 1    | 至少1名审查人批准        |
| 要求 CODEOWNER 审查 | ✅   | 涉及文件的所有者必须审查 |
| 废弃旧审查          | ✅   | 新推送后旧审查自动失效   |
| 要求 CI 通过        | ✅   | 所有状态检查必须通过     |
| 严格状态检查        | ✅   | 分支必须是最新的         |
| 要求线性历史        | ✅   | 不允许合并提交           |
| 禁止强制推送        | ✅   | 不允许 force push        |
| 禁止删除            | ✅   | 不允许删除分支           |
| 要求对话解决        | ✅   | 所有对话必须解决         |
| 管理员强制执行      | ✅   | 管理员也受规则约束       |

### 5.2 develop 分支保护规则

| 规则                | 设置 | 说明                   |
| ------------------- | ---- | ---------------------- |
| 禁止直接推送        | ✅   | 所有变更必须通过 PR    |
| 必须通过 PR         | ✅   | 不允许直推             |
| 最低审批人数        | 1    | 至少1名审查人批准      |
| 要求 CODEOWNER 审查 | ❌   | 不强制要求             |
| 废弃旧审查          | ✅   | 新推送后旧审查自动失效 |
| 要求 CI 通过        | ✅   | 基础lint检查必须通过   |
| 严格状态检查        | ❌   | 不强制要求分支最新     |
| 要求线性历史        | ❌   | 允许合并提交           |
| 禁止强制推送        | ✅   | 不允许 force push      |
| 禁止删除            | ✅   | 不允许删除分支         |
| 要求对话解决        | ✅   | 所有对话必须解决       |
| 管理员强制执行      | ❌   | 管理员可绕过           |

### 5.3 其他分支

feature、fix、release、hotfix 分支无保护规则，由命名规范和流程约束管理。

## 6. 合并策略

| 合并场景           | 合并方式        | 原因                               |
| ------------------ | --------------- | ---------------------------------- |
| feature → develop  | Squash Merge    | 一个功能一个提交，保持开发历史整洁 |
| fix → develop/main | Squash Merge    | 一个修复一个提交                   |
| develop → main     | 通过 Release PR | 详见版本发布流程                   |
| release → main     | Merge Commit    | 保留发布历史和标签                 |
| release → develop  | Merge Commit    | 回溯发布变更到开发分支             |
| hotfix → main      | Merge Commit    | 保留紧急修复历史                   |
| hotfix → develop   | Merge Commit    | 回溯紧急修复到开发分支             |

## 7. CI 流水线触发规则

| 分支       | ci-cd.yml     | ci.yml    | security.yml    | pre-commit.yml |
| ---------- | ------------- | --------- | --------------- | -------------- |
| main       | push + PR     | push + PR | push + schedule | push + PR      |
| develop    | push + PR     | -         | push            | push + PR      |
| feature/\* | PR to develop | -         | -               | -              |
| release/\* | PR to main    | push + PR | push            | push + PR      |

## 8. 日常操作指南

### 8.1 创建 Feature 分支

```bash
# 从 develop 创建 feature 分支
git checkout develop
git pull origin develop
git checkout -b feature/FR-001-alert-dedup

# 开发完成后推送
git push -u origin feature/FR-001-alert-dedup

# 在 GitHub 上创建 PR (目标: develop)
gh pr create --base develop --title "feat: alert deduplication" --body "..."
```

### 8.2 创建 Fix 分支

```bash
# 从 develop 创建 fix 分支
git checkout develop
git pull origin develop
git checkout -b fix/FR-002-login-timeout

# 如果是针对 main 的紧急修复
git checkout main
git pull origin main
git checkout -b fix/FR-010-rbac-permission
```

### 8.3 创建 Release 分支

```bash
# 仅项目负责人可创建
git checkout develop
git pull origin develop
git checkout -b release/v0.10.0

# 版本号更新、测试修复...
# 完成后创建 PR 到 main 和 develop
gh pr create --base main --title "release: v0.10.0" --body "..."
gh pr create --base develop --title "backmerge: v0.10.0 to develop" --body "..."
```

### 8.4 创建 Hotfix 分支

```bash
# 仅项目负责人可创建
git checkout main
git pull origin main
git checkout -b hotfix/v0.10.1-xss-fix

# 修复完成后创建 PR 到 main 和 develop
gh pr create --base main --title "hotfix: XSS vulnerability fix" --body "..."
gh pr create --base develop --title "backmerge: hotfix v0.10.1 to develop" --body "..."
```

### 8.5 清理已合并分支

```bash
# 删除本地已合并分支
git branch --merged develop | grep -E 'feature/|fix/' | xargs git branch -d

# 删除远程已合并分支
git branch -r --merged origin/develop | grep -E 'feature/|fix/' | sed 's/origin\///' | xargs -I{} git push origin --delete {}
```

## 9. 分支命名验证

项目提供了分支命名验证工具，可通过以下方式使用：

### Pre-commit Hook

在 `.pre-commit-config.yaml` 中已配置 `validate-branch-name` hook，每次提交时自动验证当前分支名是否符合规范。

### 手动验证

```bash
# 使用验证脚本
./scripts/validate-branch-name.sh

# 使用 Makefile 命令
make branch-validate
```

## 10. 配置文件参考

| 文件                                   | 用途                                |
| -------------------------------------- | ----------------------------------- |
| `.github/branch-protection-rules.json` | 分支保护规则配置（GitHub API 使用） |
| `scripts/setup-branch-protection.sh`   | GitHub 分支保护规则自动配置脚本     |
| `scripts/validate-branch-name.sh`      | 分支命名规范验证脚本                |

## 11. 常见问题

### Q: 分支名验证失败怎么办？

A: 检查分支名是否符合命名规范。使用 `make branch-validate` 查看详细错误信息。

### Q: 如何绕过分支保护规则？

A: develop 分支管理员可绕过；main 分支管理员不可绕过。紧急情况下使用 hotfix 流程。

### Q: feature 分支从哪个分支创建？

A: 始终从 `develop` 分支创建，合并回 `develop`。

### Q: release 分支合并后需要删除吗？

A: 是的，release 分支在合并到 main 和 develop 后应删除。删除前确保已打 Git Tag。

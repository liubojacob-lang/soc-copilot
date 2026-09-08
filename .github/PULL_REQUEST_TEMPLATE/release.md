---
name: Release PR
about: Version release pull request
title: "Release v"
labels: release
---

## 📦 版本发布

**版本号**: v

**发布类型**: <!-- MAJOR / MINOR / PATCH -->

**发布负责人**:

## 📋 变更摘要

<!-- 简要描述本次发布的主要变更 -->

## 📝 CHANGELOG

<!-- 粘贴或链接到 CHANGELOG.md 中本次版本的变更内容 -->

### Added

-

### Changed

-

### Fixed

-

### BREAKING CHANGES

-

## ✅ 发布前检查清单

### 代码变更

- [ ] 版本号已更新（`backend/pyproject.toml` + `frontend/package.json`）
- [ ] CHANGELOG.md 已更新
- [ ] 所有计划功能已合并到此分支
- [ ] 无阻塞级别的未解决问题

### 质量保障

- [ ] CI 全量检查通过
- [ ] 安全扫描无高危漏洞
- [ ] 代码审查已完成

### 兼容性

- [ ] API 变更向后兼容（或标注为 BREAKING CHANGE）
- [ ] 数据库迁移脚本已准备（如有）
- [ ] 配置变更已记录（如有新增环境变量等）

### 文档

- [ ] API 文档已更新（如有 API 变更）
- [ ] 部署文档已更新（如有部署流程变更）
- [ ] 迁移指南已编写（如有 BREAKING CHANGE）

## 🔄 合并后操作

合并后以下操作将自动执行：

1. ~~创建 Git Tag~~ → 由 GitHub Actions 自动完成
2. ~~创建 GitHub Release~~ → 由 GitHub Actions 自动完成
3. ~~构建并推送 Docker 镜像~~ → 由 GitHub Actions 自动完成
4. 合并回 develop 分支 → 由 GitHub Actions 自动完成

## ⚠️ 注意事项

<!-- 任何需要特别注意的事项，如已知问题、临时解决方案等 -->

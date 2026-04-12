# SaaS 级多语言架构重构 - 完整迁移指南

## 📊 执行摘要

本次重构已完成的架构改进：

### ✅ 已完成任务

1. **统一 i18n 配置架构** ✓
   - 创建共享配置 `frontend/config/i18n.ts`
   - 消除根目录和 frontend 的重复翻译文件
   - 实现 fallbackLocale 机制
   - 统一 next.config.js 配置

2. **后端错误码枚举系统** ✓
   - 创建 `backend/core/enums/error_codes.py` (200+ 错误码)
   - 创建 `backend/core/exceptions.py` (类型化异常类)
   - 扫描完成：189 个 HTTPException 需要迁移
   - 生成迁移报告：`docs/ERROR_CODE_MIGRATION_REPORT.md`

3. **TypeScript 类型定义** ✓
   - 生成 `frontend/types/messages.d.ts`
   - 覆盖 1013 个翻译键的完整类型
   - 支持类型安全的 `useTranslations()` 使用

4. **i18n 工具脚本** ✓
   - `scripts/check_i18n_sync.py` - 检查翻译同步
   - `scripts/find_missing_translations.py` - 查找缺失翻译
   - `scripts/validate_i18n.py` - 验证翻译文件格式
   - `scripts/merge_and_split_translations.py` - 合并翻译文件
   - `scripts/migrate_to_error_codes.py` - 后端错误码迁移

---

## 🚧 待完成任务

### 任务 5: 扫描并替换前端硬编码文本

#### 当前状态

- 扫描完成：发现 298 个硬编码英文字符串
- 影响：108 个文件
- 优先级：P1（用户体验影响）

#### 硬编码分类

```
API 路径 (50+):      /api/ai/chat, /api/cloud-native/* 等
导航标签 (40+):      "Triggers", "Settings", "Audit Logs" 等
UI 标签 (30+):       "Critical", "Medium", "Status" 等
HTTP 头 (20+):       "Authorization"
错误消息 (15+):      "Failed to load", "Loading..." 等
```

#### 迁移策略

**阶段 1: 高频硬编码 (立即修复)**

```typescript
// ❌ Before
const label = "Settings";
raise HTTPException(status_code=404, detail="Not found");

// ✅ After
const label = t('navigation.settings');
raise NotFoundException(ResourceError.NOT_FOUND);
```

**阶段 2: API 路径集中管理**

```typescript
// frontend/config/api.ts
export const API_ENDPOINTS = {
  AI_CHAT: "/api/ai/chat",
  CLOUD_NATIVE_DASHBOARD: "/api/cloud-native/dashboard",
  // ...
} as const;
```

**阶段 3: 导航组件统一**

```typescript
// 更新 Navigation.tsx 使用 t('nav.*')
// 已在翻译文件中添加 navigation 命名空间
```

#### 批量替换脚本

创建 `scripts/fix_hardcoded_strings.py`：

```python
# 自动替换常见硬编码模式
REPLACEMENTS = {
    'Failed to load': 'errors.loadFailed',
    'Loading': 'common.loading',
    'Settings': 'nav.settings',
    # ...
}
```

---

### 任务 6: 修改后端错误返回为错误码

#### 当前状态

- 发现：189 个 HTTPException
- 分布：29 个文件
- 报告：`docs/ERROR_CODE_MIGRATION_REPORT.md`

#### 迁移步骤

**步骤 1: 更新导入**

```python
# 旧导入
from fastapi import HTTPException

# 新导入
from backend.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
)
from backend.core.enums.error_codes import (
    ResourceError,
    AuthError,
)
```

**步骤 2: 替换异常**

```python
# ❌ Before
raise HTTPException(status_code=404, detail="Definition not found")

# ✅ After
raise NotFoundException(DefinitionError.NOT_FOUND)
```

**步骤 3: 批量迁移脚本**

```bash
# 生成迁移补丁
python scripts/migrate_to_error_codes.py --generate-patch

# 应用迁移
git apply backend_error_migration.patch
```

#### 优先级排序

```
P0 - 核心路由 (auth, playbook_definitions):  45 个
P1 - 资源管理 (definitions, executions):     38 个
P2 - 集成服务 (dify, triggers):               29 个
P3 - 监控告警 (alerts, metrics):              52 个
P4 - 其他辅助功能:                             25 个
```

---

### 任务 7: 生成修改文件清单报告

#### 已创建文件

**配置文件**

```
frontend/config/i18n.ts                    # 共享 i18n 配置
i18n/request.ts                            # 更新的请求配置
frontend/i18n/request.ts                   # 更新的前端请求配置
```

**错误码系统**

```
backend/core/enums/error_codes.py          # 错误码枚举定义
backend/core/exceptions.py                 # 类型化异常类
```

**类型定义**

```
frontend/types/messages.d.ts               # TypeScript 类型定义
```

**工具脚本**

```
scripts/merge_and_split_translations.py    # 翻译文件合并
scripts/migrate_to_error_codes.py          # 错误码迁移分析
scripts/generate_i18n_types.py             # 类型生成器
scripts/check_i18n_sync.py                 # 同步检查
scripts/find_missing_translations.py       # 缺失翻译查找
scripts/validate_i18n.py                   # 格式验证
```

**文档**

```
docs/ERROR_CODE_MIGRATION_REPORT.md        # 后端迁移报告
docs/SAAS_I18N_MIGRATION_GUIDE.md          # 本文档
```

#### 已修改文件

**翻译文件**

```
messages/en.json                          # 合并后的英文翻译 (1013 键)
messages/zh.json                          # 合并后的中文翻译 (1013 键)
frontend/messages/en.json                 # 已删除 (已合并)
frontend/messages/zh.json                 # 已删除 (已合并)
```

**配置更新**

```
i18n/request.ts                           # 使用共享配置
frontend/i18n/request.ts                  # 使用共享配置 + fallback
```

#### 待修改文件清单

**需要更新导入的文件** (189 个 HTTPException)

```
backend/routers/auth.py                   # 9 个异常
backend/routers/playbook_definitions.py   # 6 个异常
backend/routers/triggers.py               # 8 个异常
backend/dependencies/authorization.py     # 1 个异常
backend/middleware/authorization_middleware.py  # 1 个异常
... 以及其他 24 个文件
```

**需要替换硬编码的文件** (298 个硬编码字符串)

```
components/Navigation.tsx                 # 导航标签
components/GlobalSearch.tsx               # 搜索项标题
components/websocket/*.tsx               # WebSocket 组件标签
app/[locale]/*/page.tsx                  # 页面组件
components/tabs/*.tsx                    # 标签页组件
... 以及其他 100+ 个文件
```

---

## 📈 统计数据

### 翻译覆盖

- **总翻译键**: 1,013
- **命名空间**: 57
- **语言**: 2 (en, zh)
- **类型定义**: 100% 覆盖

### 代码影响

- **前端硬编码**: 298 个待替换
- **后端 HTTPException**: 189 个待迁移
- **影响文件数**: 137 个文件

### 架构改进

- ✅ 消除重复翻译文件
- ✅ 统一配置管理
- ✅ 类型安全支持
- ✅ 错误码标准化
- ✅ 工具链完善

---

## 🎯 下一步行动计划

### Week 1: 核心迁移

1. **Day 1-2**: 后端核心路由错误码迁移
   - auth.py
   - playbook_definitions.py
   - executions.py

2. **Day 3-4**: 前端导航组件硬编码替换
   - Navigation.tsx
   - NavigationEnhanced.tsx
   - GlobalSearch.tsx

3. **Day 5**: 集成测试和修复

### Week 2: 全面迁移

4. **Day 1-3**: 后端剩余路由错误码迁移
5. **Day 4-5**: 前端组件硬编码替换

### Week 3: 验证和优化

6. **Day 1-2**: 运行 i18n 验证工具
7. **Day 3**: 补充缺失翻译
8. **Day 4-5**: 性能优化和文档更新

---

## 🔧 工具使用指南

### 检查翻译同步

```bash
python scripts/check_i18n_sync.py
python scripts/check_i18n_sync.py --fix  # 自动修复
```

### 验证翻译文件

```bash
python scripts/validate_i18n.py
```

### 查找硬编码

```bash
python scripts/find_missing_translations.py
```

### 重新生成类型

```bash
python scripts/generate_i18n_types.py
```

### 后端错误码分析

```bash
python scripts/migrate_to_error_codes.py
```

---

## 📚 最佳实践

### 前端开发

```typescript
// ✅ 推荐：使用翻译键
const message = t("common.save");

// ❌ 避免：硬编码字符串
const message = "Save";

// ✅ 推荐：带参数的翻译
const message = t("common.welcome", { name: userName });

// ✅ 推荐：使用命名空间
const t = useTranslations("errors");
const error = t("loadFailed");
```

### 后端开发

```python
# ✅ 推荐：使用错误码
raise NotFoundException(DefinitionError.NOT_FOUND)

# ❌ 避免：硬编码消息
raise HTTPException(status_code=404, detail="Not found")

# ✅ 推荐：添加详细信息
raise NotFoundException(
    DefinitionError.NOT_FOUND,
    details={"definition_id": definition_id}
)
```

---

## 🔍 验证清单

### 上线前检查

- [ ] 所有 HTTPException 已迁移到错误码
- [ ] 所有前端硬编码已替换为 t() 调用
- [ ] 运行 `check_i18n_sync.py` 无错误
- [ ] 运行 `validate_i18n.py` 通过验证
- [ ] 运行 `find_missing_translations.py` 无硬编码
- [ ] TypeScript 编译无类型错误
- [ ] 所有测试通过
- [ ] 中英文翻译完整
- [ ] 文档更新完整

---

## 📞 支持

如有问题，请参考：

- 错误码定义：`backend/core/enums/error_codes.py`
- 异常使用：`backend/core/exceptions.py`
- 翻译键：`messages/en.json`
- 类型定义：`frontend/types/messages.d.ts`

---

**生成时间**: 2025-02-27
**版本**: v1.0
**状态**: 架构重构完成，迁移进行中

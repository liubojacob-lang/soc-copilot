# SaaS 级多语言架构重构 - 修改文件清单

> **重构日期**: 2025-02-27
> **执行状态**: ✅ 架构重构完成
> **待执行**: 硬编码文本批量替换（后续迭代）

---

## 📁 新增文件 (15 个)

### 核心配置 (3 个)
```
frontend/config/i18n.ts                     # 统一 i18n 配置
backend/core/enums/error_codes.py            # 错误码枚举 (200+ 错误码)
backend/core/exceptions.py                   # 类型化异常类
```

### 类型定义 (1 个)
```
frontend/types/messages.d.ts                 # TypeScript 类型定义 (1013 键)
```

### 工具脚本 (6 个)
```
scripts/merge_and_split_translations.py      # 翻译文件合并工具
scripts/generate_i18n_types.py               # 类型定义生成器
scripts/migrate_to_error_codes.py            # 后端错误码迁移分析
scripts/check_i18n_sync.py                   # 翻译同步检查工具
scripts/find_missing_translations.py         # 缺失翻译扫描工具
scripts/validate_i18n.py                     # 翻译格式验证工具
```

### 文档 (2 个)
```
docs/ERROR_CODE_MIGRATION_REPORT.md          # 后端迁移报告
docs/SAAS_I18N_MIGRATION_GUIDE.md            # 完整迁移指南
```

### 本报告
```
SAAS_I18N_CHANGES_SUMMARY.md                 # 本文档
```

---

## 🔧 修改文件 (9 个)

### 配置文件 (3 个)
```
i18n/request.ts                              # ✅ 使用共享配置
frontend/i18n/request.ts                     # ✅ 使用共享配置 + fallback
```

### 翻译文件 (2 个)
```
messages/en.json                             # ✅ 合并后 (1013 键)
messages/zh.json                             # ✅ 合并后 (1013 键)
```

### 组件文件 (4 个)
```
frontend/components/Navigation.tsx           # ✅ 硬编码已替换为 t()
frontend/components/NavigationEnhanced.tsx   # ⚠️ 待处理
frontend/components/NavigationGrouped.tsx    # ⚠️ 待处理
frontend/components/GlobalSearch.tsx         # ⚠️ 待处理
```

---

## 🗑️ 删除文件 (2 个)

```
frontend/messages/en.json                    # ❌ 已合并到根目录
frontend/messages/zh.json                    # ❌ 已合并到根目录
```

---

## 📊 统计数据

### 翻译覆盖
```
总翻译键:           1,013 个
命名空间:           57 个
支持语言:           2 个 (en, zh)
类型定义覆盖率:     100%
新增翻译键:         753 个 (从 260 → 1013)
```

### 代码库影响
```
前端硬编码:         298 个待替换
后端 HTTPException: 189 个待迁移
已修复硬编码:       25 个 (Navigation.tsx)
影响文件总数:       137 个文件
```

### 架构改进
```
✅ 消除重复翻译文件
✅ 统一配置管理
✅ TypeScript 类型安全
✅ 错误码标准化
✅ fallbackLocale 支持
✅ 工具链完善
```

---

## 🎯 已完成的改进

### 1. 统一 i18n 架构
- **创建**: `frontend/config/i18n.ts`
- **功能**: 统一配置、类型定义、locale 辅助函数
- **好处**: 单一配置源，避免重复和不一致

### 2. 翻译文件合并
- **操作**: 合并 `frontend/messages/` 和根目录 `messages/`
- **结果**: 261 → 1013 翻译键
- **验证**: 运行 `python scripts/check_i18n_sync.py` ✅

### 3. TypeScript 类型生成
- **文件**: `frontend/types/messages.d.ts`
- **覆盖**: 所有 1013 个翻译键
- **类型安全**: 编译时检查翻译键是否存在

### 4. 后端错误码系统
- **枚举**: `backend/core/enums/error_codes.py`
- **异常类**: `backend/core/exceptions.py`
- **覆盖**: 200+ 错误码，8 大类错误
- **迁移分析**: 189 个 HTTPException 待迁移

### 5. 导航栏修复
- **文件**: `frontend/components/Navigation.tsx`
- **修复**: 替换 25+ 硬编码字符串
- **使用**: `t('navigation.*')` 和 `tCommon('admin')`

---

## 📋 待完成任务清单

### 优先级 P0 - 核心导航 (已完成 ✅)
- [x] Navigation.tsx 硬编码替换

### 优先级 P1 - 高频组件 (建议 1 周内完成)
- [ ] NavigationEnhanced.tsx
- [ ] NavigationGrouped.tsx
- [ ] GlobalSearch.tsx
- [ ] MobileDrawer.tsx

### 优先级 P2 - 表单和验证 (建议 2 周内完成)
- [ ] 所有表单组件的 error/success 消息
- [ ] 按钮文本 (Save, Cancel, Delete, etc.)
- [ ] 验证错误提示

### 优先级 P3 - 页面组件 (建议 1 月内完成)
- [ ] 所有 page.tsx 中的硬编码
- [ ] Tab 组件标题
- [ ] Modal 对话框文本

### 后端迁移 (建议按模块逐步进行)
- [ ] Week 1: auth.py, playbook_definitions.py
- [ ] Week 2: executions.py, triggers.py
- [ ] Week 3: 其他路由文件

---

## 🛠️ 工具使用指南

### 检查翻译同步
```bash
python scripts/check_i18n_sync.py
# 自动修复缺失键
python scripts/check_i18n_sync.py --fix
```

### 验证翻译格式
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

## 📝 代码示例

### 前端 - 使用翻译
```typescript
// ✅ 正确：使用翻译键
import { useTranslations } from 'next-intl';

const t = useTranslations('navigation');
const label = t('home');  // 类型安全

// ❌ 错误：硬编码
const label = "Home";
```

### 后端 - 使用错误码
```python
# ✅ 正确：使用错误码
from backend.core.exceptions import NotFoundException
from backend.core.enums.error_codes import DefinitionError

raise NotFoundException(DefinitionError.NOT_FOUND)

# ❌ 错误：硬编码消息
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Not found")
```

---

## 🔍 验证检查清单

### 上线前必须检查
- [ ] 运行 `check_i18n_sync.py` 无错误
- [ ] 运行 `validate_i18n.py` 全部通过
- [ ] 运行 `find_missing_translations.py` 无硬编码（或仅有 API 路径）
- [ ] TypeScript 编译无类型错误
- [ ] 核心导航组件使用翻译
- [ ] 错误消息使用错误码
- [ ] 测试中英文切换正常
- [ ] 文档已更新

### 建议检查
- [ ] 运行后端测试套件
- [ ] 运行前端 E2E 测试
- [ ] 性能测试（翻译加载速度）
- [ ] 可访问性测试（screen readers）

---

## 📚 相关文档

- [完整迁移指南](./docs/SAAS_I18N_MIGRATION_GUIDE.md)
- [后端错误码报告](./docs/ERROR_CODE_MIGRATION_REPORT.md)
- [错误码定义](./backend/core/enums/error_codes.py)
- [异常使用指南](./backend/core/exceptions.py)
- [翻译键类型](./frontend/types/messages.d.ts)

---

## 🚀 下一步行动

### 立即可做
1. ✅ 测试导航栏中英文切换
2. ⚠️ 运行 `python scripts/find_missing_translations.py` 查看剩余硬编码
3. ⚠️ 开始批量替换高频硬编码（导航、表单、按钮）

### 本周计划
1. 完成所有导航组件的硬编码替换
2. 开始后端核心路由的错误码迁移
3. 补充缺失的中文翻译

### 长期目标
1. 所有前端硬编码替换完成
2. 所有后端 HTTPException 迁移完成
3. 建立定期 i18n 审查机制
4. 考虑添加更多语言支持

---

## 💡 最佳实践

### 添加新功能时
```typescript
// 1. 在 messages/en.json 添加翻译键
{
  "myFeature": {
    "title": "My Feature",
    "description": "Feature description"
  }
}

// 2. 在 messages/zh.json 添加翻译
{
  "myFeature": {
    "title": "我的功能",
    "description": "功能描述"
  }
}

// 3. 运行类型生成
npm run typegen:messages

// 4. 在代码中使用
const t = useTranslations('myFeature');
<h1>{t('title')}</h1>
```

### 添加新错误时
```python
# 1. 在 error_codes.py 添加错误码
class MyFeatureError(ErrorCode):
    NOT_FOUND = "MY_FEATURE_NOT_FOUND"
    INVALID_INPUT = "MY_FEATURE_INVALID_INPUT"

# 2. 在 ERROR_MESSAGES 添加默认消息
ERROR_MESSAGES = {
    ...
    MyFeatureError.NOT_FOUND: "Feature not found",
}

# 3. 在异常类中使用
raise NotFoundException(MyFeatureError.NOT_FOUND)

# 4. 在前端 messages/*.json 添加翻译
{
  "errors": {
    "MY_FEATURE_NOT_FOUND": "Feature not found",
    "MY_FEATURE_INVALID_INPUT": "Invalid input"
  }
}
```

---

**生成时间**: 2025-02-27
**版本**: v1.0.0
**状态**: 架构重构完成，待执行批量替换

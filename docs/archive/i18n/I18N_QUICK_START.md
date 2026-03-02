# i18n 工具快速参考

## 验证命令

```bash
# 检查翻译同步
python scripts/check_i18n_sync.py

# 自动修复缺失键
python scripts/check_i18n_sync.py --fix

# 验证翻译格式
python scripts/validate_i18n.py

# 查找硬编码
python scripts/find_missing_translations.py

# 生成类型定义
python scripts/generate_i18n_types.py

# 后端错误码分析
python scripts/migrate_to_error_codes.py
```

## package.json 添加脚本

```json
{
  "scripts": {
    "i18n:check": "python scripts/check_i18n_sync.py",
    "i18n:fix": "python scripts/check_i18n_sync.py --fix",
    "i18n:validate": "python scripts/validate_i18n.py",
    "i18n:find": "python scripts/find_missing_translations.py",
    "typegen:messages": "python scripts/generate_i18n_types.py",
    "backend:analyze-errors": "python scripts/migrate_to_error_codes.py"
  }
}
```

## 使用示例

```bash
# 开发流程
npm run i18n:validate    # 验证格式
npm run typegen:messages # 生成类型
npm run i18n:check       # 检查同步

# 修复问题
npm run i18n:fix         # 自动修复缺失键
npm run i18n:find        # 查找硬编码
```

# Database Migrations Guide

## Overview

SOC Copilot uses **Alembic** for database schema migrations. Migrations are automatically run on application startup.

> **v1.5 变更**: 历史上 22 个增量迁移文件已合并（squash）为全量基线：
> `0001_full_baseline`（46 张表全量建表）→ `0002_performance_indexes`（性能索引）。
> 全新部署无需关心旧链；**已有旧版本数据库的升级见下方 Runbook**。

## Directory Structure

```
backend/
├── alembic.ini              # Alembic configuration
├── migrate.py               # Migration helper script
├── migrations/              # Old SQL migrations (deprecated)
├── migrations_alembic/      # Alembic migrations
│   ├── env.py              # Migration environment configuration
│   ├── script.py.mako      # Migration template
│   └── versions/
│       ├── 0001_full_baseline.py        # Squashed full-schema baseline
│       └── 0002_performance_indexes.py  # Performance indexes
└── models/                 # SQLAlchemy models
```

## Automatic Migration on Startup

Migrations are automatically run when the application starts.

- **development**: 迁移失败仅记录 warning，应用继续启动。
- **production**: 迁移失败会**中止启动**（fail-fast）。容器退出后由 `restart: always` 重试，修复配置前不会带着错误 schema 运行。

## Fresh Deployment (新部署)

全新数据库无需任何手动步骤：应用启动时自动执行 `alembic upgrade head`，
依次创建 `0001_full_baseline`（全部表结构）和 `0002_performance_indexes`。

如果数据库由外部工具（如 `Base.metadata.create_all`）预先建过表，只需打标记：

```bash
alembic stamp 0002_performance_indexes
```

## Runbook: 升级旧版本数据库（v0.x–v1.4 → v1.5+）

旧版本库的 `alembic_version` 里记录的是已删除的旧 revision（如
`v1_4_0_prompt_registry`），新链无法定位，直接 `upgrade head` 会报错。
按以下步骤桥接：

### 0. 前置确认

- 确认旧库 schema 与 `0001_full_baseline` 的目标 schema 一致（见步骤 3 的 diff 校验）。
- 若旧库落后于 v1.4（未跑完旧链），先用旧版本代码补齐到 v1.4 再执行本 runbook。

### 1. 备份

```bash
pg_dump -h <host> -U <user> -Fc <dbname> > backup_$(date +%Y%m%d_%H%M).dump
```

### 2. 标记基线（不改 schema）

```bash
cd backend
alembic stamp 0001_full_baseline   # 声明：当前 schema 等价于基线
alembic upgrade head               # 应用 0002_performance_indexes
```

> `stamp` 只更新 `alembic_version` 表，不执行任何 DDL。

### 3. 校验无漂移（重要）

用 autogenerate 对比模型与实际 schema，**预期输出为空 diff**：

```bash
alembic revision --autogenerate -m "post-upgrade drift check"
# 检查生成的文件：应只有 pass 或者可忽略的命名差异
# 确认后删除该检查文件，不要应用它
```

如果 diff 非空，说明旧库与基线存在漂移：先人工核对差异，
将检查文件改造为修复迁移（或手工对齐 schema）后再重新 stamp。

### 4. 回滚预案

```bash
# 应用层回滚：使用上一版本镜像重新部署
# 数据回滚：
pg_restore -h <host> -U <user> -d <dbname> --clean backup_xxx.dump
```

`0002_performance_indexes` 的 `downgrade()` 仅删除索引，可安全执行：
`alembic downgrade 0001_full_baseline`。

## Manual Migration Commands

### Run all pending migrations

```bash
cd backend
python migrate.py
```

### Using Alembic directly

```bash
cd backend

# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history

# Create new migration
alembic revision -m "description"
```

## Creating a New Migration

### 1. Modify your model

```python
# models/playbook_run.py
class PlaybookRunModel(Base):
    # ... existing fields ...
    new_field: Mapped[str] = mapped_column(String(100))
```

### 2. Generate migration

```bash
cd backend
alembic revision --autogenerate -m "add new_field to playbook_run"
```

### 3. Review the generated migration

Check `migrations_alembic/versions/<revision_id>_description.py` to ensure it's correct.

### 4. Apply the migration

```bash
alembic upgrade head
# Or just restart the application (migrations run automatically)
```

## Troubleshooting

### Migration conflict

If a migration fails, you can:

1. Check the error message
2. Manually fix the database
3. Use `alembic stamp head` to mark as applied (use carefully!)

### Production startup fails with "Database migration failed"

生产环境迁移失败会阻断启动（有意设计）。查看容器日志中的 Migration output 定位原因，
修复后容器会自动重试。不要通过关闭校验绕过。

### View applied migrations

```bash
alembic current
```

## Best Practices

1. **Always review** auto-generated migrations before applying
2. **Test migrations** on a copy of production database first
3. **Back up your database** before running major migrations
4. **Keep migrations reversible** - implement both `upgrade()` and `downgrade()`
5. **Never modify** applied migrations - create new ones instead

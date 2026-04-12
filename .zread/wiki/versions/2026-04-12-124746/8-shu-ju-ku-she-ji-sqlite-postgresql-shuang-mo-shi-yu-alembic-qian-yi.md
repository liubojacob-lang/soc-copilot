SOC Copilot 的持久化层建立在 **SQLAlchemy 异步 ORM** 之上，通过环境变量 `DATABASE_URL` 在 **SQLite（开发/测试）** 和 **PostgreSQL（生产）** 之间无缝切换。Schema 版本管理采用 **Alembic** 迁移框架，配合 `DatabaseService` 生命周期服务在应用启动时自动执行升级。本文将从架构选型动机、连接管理机制、模型体系、迁移链路四个维度展开，帮助开发者理解双模式数据库的设计决策与实操要点。

Sources: [db/session.py](backend/db/session.py#L1-L128), [core/config.py](backend/core/config.py#L78-L83)

## 架构选型：为什么需要双模式？

SOC Copilot 面向两类截然不同的部署场景：**单机开发调试**（快速启动、零依赖）和 **团队/生产部署**（高并发、持久化、多实例共享）。单一的数据库方案无法同时满足这两种需求——SQLite 不支持并发写入且缺乏连接池，PostgreSQL 的运维成本对于本地开发者而言过高。双模式设计因此成为必然选择。

```mermaid
graph TD
    A[DATABASE_URL 环境变量] --> B{数据库类型判断}
    B -->|sqlite 前缀| C[SQLite 引擎<br/>aiosqlite + NullPool]
    B -->|postgresql 前缀| D[PostgreSQL 引擎<br/>asyncpg + 连接池]
    C --> E[async_sessionmaker]
    D --> E
    E --> F[AsyncSessionLocal]
    F --> G[get_session 依赖注入]
    G --> H[FastAPI 路由层]
    
    style A fill:#f9f,stroke:#333
    style C fill:#ff9,stroke:#333
    style D fill:#9cf,stroke:#333
```

核心判断逻辑位于 `db/session.py` 中：模块加载时读取 `DATABASE_URL` 环境变量，通过前缀匹配 (`sqlite` vs `postgresql`) 决定引擎创建策略。SQLite 使用 `NullPool`（每次请求新建连接），PostgreSQL 启用连接池（`pool_size=20, max_overflow=40`）。这种"编译时分支"模式意味着切换数据库只需修改一个环境变量，无需改动任何业务代码。

Sources: [db/session.py](backend/db/session.py#L26-L87)

### 双模式参数对比

| 特性 | SQLite 模式 | PostgreSQL 模式 |
|------|------------|-----------------|
| **适用场景** | 本地开发、单元测试 | 生产部署、Docker Compose |
| **异步驱动** | `aiosqlite` | `asyncpg` |
| **连接池策略** | `NullPool`（无池化） | `pool_size=20, max_overflow=40` |
| **默认存储位置** | `data/app.db` | Docker volume `postgres_data` |
| **并发写入** | 不支持（`check_same_thread=False` 仅允许跨线程读） | 完全支持 |
| **URL 格式** | `sqlite+aiosqlite:///data/app.db` | `postgresql+asyncpg://user:pass@host/db` |
| **连接回收** | 不适用 | `pool_recycle=3600`（每小时） |
| **预检 ping** | 不适用 | `pool_pre_ping=True` |

Sources: [db/session.py](backend/db/session.py#L39-L87), [core/config.py](backend/core/config.py#L78-L83)

## 连接管理与会话生命周期

### 引擎创建与连接池配置

引擎创建过程分为三个分支。SQLite 分支的核心考量是避免连接泄漏——SQLite 不支持真正的连接池，因此强制使用 `NullPool`，每次请求结束后立即归还连接。`connect_args={"check_same_thread": False}` 允许跨线程共享连接（FastAPI 的异步特性需要这一点）。PostgreSQL 分支则配置了完整的连接池参数，这些参数来自 `Settings` 配置类，可通过环境变量覆盖。

Sources: [db/session.py](backend/db/session.py#L38-L87)

PostgreSQL 连接 URL 还有一层**自动协议转换**机制：如果传入的 URL 使用同步驱动前缀（`postgresql://` 或 `postgresql+psycopg2://`），模块会自动替换为 `postgresql+asyncpg://`，确保与 SQLAlchemy 异步引擎兼容。这意味着开发者可以直接使用 Docker Compose 中定义的 `postgresql://` 格式 URL，无需手动调整。

Sources: [db/session.py](backend/db/session.py#L58-L66)

### 会话工厂与依赖注入

`AsyncSessionLocal` 是基于 `async_sessionmaker` 创建的会话工厂，配置了 `expire_on_commit=False`——这是异步 ORM 的关键设置。默认情况下 SQLAlchemy 在 commit 后会 expire 所有已加载的对象，导致后续属性访问触发新的查询；但在异步上下文中，这种隐式查询会引发 `MissingGreenlet` 异常。`expire_on_commit=False` 确保对象在 commit 后仍然可用。

`get_session()` 是 FastAPI 的依赖注入函数，采用生成器模式管理会话生命周期：正常执行路径自动 commit，异常路径自动 rollback，finally 块确保连接关闭。这种"**try-commit-except-rollback-finally-close**"模式是异步数据库会话管理的最佳实践。

Sources: [db/session.py](backend/db/session.py#L89-L116)

### 测试环境隔离

测试环境通过 `conftest.py` 设置 `ENVIRONMENT=test`，触发独立的数据库路径配置。SQLite 测试模式下使用 `/tmp/soc_copilot_test.db` 而非开发库的 `data/app.db`，确保测试数据不会污染开发数据。`conftest.py` 的 `setup_test_database` fixture 在会话开始前删除旧测试库、结束后清理，实现了完全的测试隔离。

Sources: [db/session.py](backend/db/session.py#L23-L36), [conftest.py](backend/conftest.py#L11-L36)

## 模型体系：30+ 表的领域建模

### 核心模型层次

项目的 34 个模型文件定义了超过 30 张数据库表，覆盖用户认证、告警管理、Playbook 编排、威胁情报、审计日志等完整的安全运营领域。所有模型继承自 `db.session.Base`（SQLAlchemy 的 `declarative_base()`），并通过 `models/__init__.py` 统一导出。

```mermaid
erDiagram
    users ||--o{ audit_logs : "user_id"
    users ||--o{ playbook_runs : "created_by"
    users ||--o{ playbook_definitions : "created_by"
    
    playbook_definitions ||--o{ playbook_nodes : "definition_id"
    playbook_definitions ||--o{ playbook_edges : "definition_id"
    playbook_definitions ||--o{ playbook_triggers : "definition_id"
    playbook_definitions ||--o{ playbook_runs : "definition_id"
    
    playbook_runs ||--o{ playbook_run_steps : "run_id CASCADE"
    playbook_runs ||--o{ playbook_node_runs : "run_id CASCADE"
    playbook_runs ||--o{ playbook_approvals : "run_id CASCADE"
    
    playbook_node_runs ||--o{ playbook_node_attempts : "node_run_id CASCADE"
    
    correlation_rules ||--o{ correlated_events : "rule_id"
    
    security_alerts ||--o{ alert_notes : "alert_id"
    
    roles ||--o{ role_permissions : "role_id"
    permissions ||--o{ role_permissions : "permission_id"
```

Sources: [models/__init__.py](backend/models/__init__.py#L1-L65)

### 主键策略：UUID 字符串

所有核心业务表采用 **UUID v4 字符串** 作为主键（`String(36)`），而非自增整数。这一决策基于三个考量：第一，UUID 在分布式环境中天然唯一，为未来的多实例部署预留了空间；第二，UUID 不暴露记录的创建顺序和总量，降低了信息泄露风险；第三，Playbook 引擎中的节点 ID 需要与 DAG 图中的逻辑 ID 保持一致，UUID 的预生成特性恰好满足此需求。

Sources: [models/user.py](backend/models/user.py#L26), [models/playbook_run.py](backend/playbook_run#L17-L19)

### 时间戳处理模式

项目中存在两种时间戳存储模式，反映了架构演进的痕迹。**早期模型**（如 `UserModel`、`AuditLogModel`）使用 `String(30)` 存储 ISO 格式时间字符串，通过 `datetime.now(UTC).isoformat()` 生成默认值。**后期模型**（如 `PlaybookDefinitionModel`）使用 `DateTime(timezone=True)` 原生类型。两种模式在 SQLite 和 PostgreSQL 下均能正常工作——SQLite 将日期存储为字符串，PostgreSQL 使用原生 timestamp 类型。混合使用不会导致功能问题，但新模型应优先采用 `DateTime(timezone=True)` 以获得更好的类型安全和查询能力。

Sources: [models/user.py](backend/models/user.py#L37-L45), [models/playbook_definition.py](backend/models/playbook_definition.py#L32-L42)

### 多租户预留设计

`TenantMixin` 定义了 `tenant_id` 字段（`String(64), nullable=False, index=True, default="default"`），核心业务模型（如 `UserModel`、`CorrelationRule`、`SecurityAlert`）已集成此字段。`v1_1_0_arch_upgrade` 迁移为 `security_alerts`、`correlation_rules`、`users` 表添加了 `tenant_id` 列和对应索引。目前所有数据默认归入 `"default"` 租户，这是一个典型的 **Schema-first 预留** 策略——数据库层面提前准备好多租户能力，业务逻辑暂不启用。

Sources: [models/tenant_mixin.py](backend/models/tenant_mixin.py#L1-L11), [models/user.py](backend/models/user.py#L27-L29), [v1_1_0_arch_upgrade.py](backend/migrations_alembic/versions/v1_1_0_arch_upgrade.py#L19-L50)

## Alembic 迁移体系

### 迁移架构

项目使用 Alembic 管理 Schema 版本，迁移脚本存放在 `backend/migrations_alembic/versions/` 目录。`env.py` 配置了**异步迁移支持**——通过 `async_engine_from_config` 创建异步引擎，再通过 `run_sync` 在异步上下文中执行同步的 Alembic 操作。`target_metadata = Base.metadata` 使 Alembic 的 `autogenerate` 功能能够对比模型定义与实际 Schema，自动生成迁移脚本。

```mermaid
graph LR
    A[alembic.ini] -->|sqlalchemy.url| B[env.py]
    B -->|import| C[models/*]
    C -->|Base.metadata| D[target_metadata]
    D -->|autogenerate| E[新迁移脚本]
    B -->|run_async_migrations| F[异步引擎执行]
    
    G[main.py lifespan] -->|run_migrations| H[子进程调用 alembic upgrade head]
    
    style A fill:#f9f,stroke:#333
    style E fill:#9f9,stroke:#333
    style H fill:#ff9,stroke:#333
```

Sources: [migrations_alembic/env.py](backend/migrations_alembic/env.py#L1-L107), [alembic.ini](backend/alembic.ini#L89-L89)

### 迁移链路与版本历史

项目当前包含 19 个迁移脚本，形成了完整的版本演进链路。以下是关键里程碑：

| 迁移版本 | 功能 | 模式 |
|----------|------|------|
| `475ad8e8fb9b` | 初始空迁移（基线） | 基线 |
| `63fcc448222d` | v0.7.0 DAG Playbook 引擎 | 建表 |
| `e8521c2c56f4` | 用户安全列（密码历史、锁定） | 加列 |
| `v0_7_1` ~ `v0_7_8` | 触发器、审批、版本管理、AI 模型管理等 | 渐进加列/建表 |
| `v0_8_0_event_correlation` | 事件关联引擎 4 张表 | 建表 |
| `v0_9_0_performance_indexes` | 性能优化复合索引 | 加索引 |
| `v1_1_0_arch_upgrade` | 多租户 + RBAC 表 | 加列 + 建表 |
| `v1_2_0_alert_deduplication` | 告警去重与聚合字段 | 加列 + 加索引 |
| `4e9cf37ad513` | 合并分支头 | 合并 |

Sources: [migrations_alembic/versions/](backend/migrations_alembic/versions/)

### 分支合并策略

`4e9cf37ad513_merge_heads.py` 是一个典型的 **Alembic merge migration**——当两个并行开发的迁移分支（`v0_8_1_alert_notes` 和 `v1_2_0_alert_deduplication`）共享同一个 `down_revision` 时，Alembic 无法确定线性顺序，需要通过 merge 迁移将两个分支头合并为一个。合并迁移本身不包含 Schema 变更，仅声明 `down_revision = ("v0_8_1_alert_notes", "v1_2_0_alert_deduplication")`，使得后续迁移能够从合并点继续线性延伸。

Sources: [4e9cf37ad513_merge_heads.py](backend/migrations_alembic/versions/4e9cf37ad513_merge_heads.py#L1-L33)

### 启动时自动迁移

应用通过 `main.py` 的 `lifespan` 函数在启动时自动执行迁移。`run_migrations()` 函数使用 `asyncio.to_thread` 在线程池中执行 `alembic upgrade head` 子进程命令，避免阻塞事件循环。这一设计意味着**生产环境中每次部署新版本时，数据库 Schema 会自动升级到最新状态**，无需手动干预。

Sources: [main.py](backend/main.py#L143-L186)

值得注意的是，系统同时保留了两种 Schema 初始化机制：`init_db()` 通过 `Base.metadata.create_all` 直接创建所有表（用于开发环境首次启动），而 Alembic 迁移则用于版本间的增量升级。两者在首次部署时可能产生冲突——`init_db()` 创建的表没有 Alembic 版本记录，导致后续迁移可能重复执行。在实际操作中，建议统一使用 Alembic 管理所有 Schema 变更。

Sources: [db/session.py](backend/db/session.py#L118-L128), [database_service.py](backend/services/lifecycle/database_service.py#L33-L40)

## Repository 模式：数据访问抽象

### BaseRepository 泛型基类

数据访问层通过 `BaseRepository` 泛型基类提供标准化的 CRUD 操作。基类封装了 `get`、`list`（支持过滤/排序/分页）、`count`、`create`、`update`、`delete`、`bulk_update`、`bulk_delete`、`exists`、`get_or_create` 等通用方法，具体 Repository 只需继承并指定模型类型即可获得完整的数据操作能力。这种设计使得所有数据访问都通过统一的接口，便于添加横切关注点（如缓存、审计、多租户过滤）。

Sources: [repositories/base.py](backend/repositories/base.py#L1-L174)

### 双模式下的注意事项

SQLite 和 PostgreSQL 在 SQL 方言上存在微妙差异，Repository 层的查询语句需要兼容两者。项目目前主要使用 SQLAlchemy Core 的标准 API（`select`、`where`、`func.count` 等），这些 API 会由 SQLAlchemy 自动适配不同方言。但开发者需要注意以下 SQLite 限制：

- **ALTER TABLE 限制**：SQLite 不支持 `DROP COLUMN`（3.35.0 之前）和 `ALTER COLUMN`，Alembic 在 SQLite 下会使用 batch 模式（创建新表 → 复制数据 → 删除旧表 → 重命名）
- **JSON 类型**：SQLite 将 JSON 存储为 TEXT，查询时需使用 `json_extract` 而非 PostgreSQL 的 `->>` 操作符。SQLAlchemy 的 `JSON` 类型会自动处理这一差异
- **布尔类型**：SQLite 使用 0/1 整数表示布尔值，`Boolean` 列类型会自动映射
- **SERIAL/IDENTITY**：SQLite 不支持自增主键以外的序列类型

Sources: [migrations/v0.7_add_dag_support.sql](backend/migrations/v0.7_add_dag_support.sql#L1-L186)

## 生产部署的数据库配置

### Docker Compose 配置

生产部署通过 Docker Compose 使用 PostgreSQL 15 Alpine 镜像，关键配置包括：数据库凭证通过环境变量注入（`DB_USER`、`DB_PASSWORD`、`DB_NAME`），`healthcheck` 确保 PostgreSQL 完全就绪后 Backend 服务才启动，数据持久化通过 Docker volume `postgres_data` 实现，端口仅绑定 `127.0.0.1` 防止外部直接访问。

Backend 容器的 `DATABASE_URL` 直接指向内部网络中的 PostgreSQL 服务：`postgresql+asyncpg://soc_copilot:${DB_PASSWORD}@postgres:5432/soc_copilot`。内部网络 `database-net` 标记为 `internal: true`，阻止外部网络访问数据库。

Sources: [docker-compose.yml](docker-compose.yml#L5-L91)

### 连接池调优参数

PostgreSQL 连接池参数通过 `Settings` 类管理，可完全通过环境变量覆盖。默认值针对中等规模部署调优：`db_pool_size=20`（基础连接数）、`db_max_overflow=40`（最大溢出连接，峰值可达 60 个并发连接）、`db_pool_timeout=30`（等待连接的超时秒数）、`db_pool_recycle=3600`（每小时回收连接防止服务端断开）、`db_pool_pre_ping=True`（使用前验证连接有效性）。

Sources: [core/config.py](backend/core/config.py#L78-L83)

## 常用操作指南

### 创建新迁移

在 `backend/` 目录下执行以下命令创建自动生成的迁移脚本：

```bash
cd backend
alembic -c alembic.ini revision --autogenerate -m "描述信息"
```

Alembic 会对比 `Base.metadata` 中的模型定义与数据库实际 Schema，自动生成 `upgrade()` 和 `downgrade()` 函数。生成后务必检查脚本内容——自动生成可能遗漏复杂的约束（如部分索引、表达式索引），也可能包含意外的表删除。

### 手动执行迁移

```bash
# 升级到最新版本
cd backend && python -m alembic -c alembic.ini upgrade head

# 回退一个版本
cd backend && python -m alembic -c alembic.ini downgrade -1

# 查看当前版本
cd backend && python -m alembic -c alembic.ini current
```

### 切换数据库模式

SQLite → PostgreSQL 只需设置环境变量：

```bash
export DATABASE_URL="postgresql+asyncpg://soc_copilot:your_password@localhost:5432/soc_copilot"
```

PostgreSQL → SQLite（用于本地开发）则移除或清空 `DATABASE_URL`，系统会自动回退到 SQLite 默认路径。

Sources: [migrate.py](backend/migrate.py#L1-L42), [db/session.py](backend/db/session.py#L26-L30)

## 延伸阅读

- 了解数据库如何在应用启动时初始化，参见 [服务生命周期管理与优先级启动机制](7-fu-wu-sheng-ming-zhou-qi-guan-li-yu-you-xian-ji-qi-dong-ji-zhi)
- 了解模型如何映射到具体的 API 接口，参见 [后端分层架构：路由、服务、仓储与模型](6-hou-duan-fen-ceng-jia-gou-lu-you-fu-wu-cang-chu-yu-mo-xing)
- 了解 RBAC 表（roles、permissions）如何支撑权限体系，参见 [RBAC 权限模型：角色、权限与资源级访问控制](16-rbac-quan-xian-mo-xing-jiao-se-quan-xian-yu-zi-yuan-ji-fang-wen-kong-zhi)
- 了解审计日志表的写入路径，参见 [中间件链：审计、幂等性、请求追踪与异常捕获](19-zhong-jian-jian-lian-shen-ji-mi-deng-xing-qing-qiu-zhui-zong-yu-yi-chang-bu-huo)
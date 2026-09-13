#!/usr/bin/env python3
"""
SOC Copilot 数据同步脚本
将宿主机本地开发数据库 (data/app.db) 的全量业务数据同步至独立仿真环境 (soc-postgres-sim)。

使用方式:
    python3 scripts/sync_dev_to_sim.py
"""

import json
from datetime import datetime
from dateutil import parser as date_parser
from sqlalchemy import create_engine, MetaData, text, Boolean, DateTime, JSON

SQLITE_URL = "sqlite:///data/app.db"
PG_URL = "postgresql://soc_sim_user:soc_sim_password_123456@127.0.0.1:15432/soc_sim_db"

def convert_value(val, col_type):
    if val is None:
        return None
    
    # 布尔字段转换 (SQLite 0/1 -> PG True/False)
    if isinstance(col_type, Boolean):
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("true", "1", "t", "yes")
        return bool(val)
    
    # 时间字段转换
    if isinstance(col_type, DateTime):
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            try:
                return datetime.fromisoformat(val)
            except Exception:
                try:
                    return date_parser.parse(val)
                except Exception:
                    return None
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val)
            except Exception:
                return None
        return val

    # JSON 字段转换
    if isinstance(col_type, JSON):
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    return val


def run_sync():
    print("🚀 开始连接开发数据库 (SQLite) 与仿真数据库 (PostgreSQL)...")
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(PG_URL)

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    excluded_tables = {"alembic_version"}

    with pg_engine.begin() as pg_conn:
        # 暂时关闭外键检查避免导入次序约束
        pg_conn.execute(text("SET session_replication_role = 'replica';"))

        tables_to_sync = [
            t_name for t_name in pg_meta.tables.keys()
            if t_name not in excluded_tables and t_name in sqlite_meta.tables
        ]

        print(f"🧹 准备清理仿真数据库中的旧数据 ({len(tables_to_sync)} 张表)...")
        for t_name in tables_to_sync:
            pg_conn.execute(text(f'TRUNCATE TABLE "{t_name}" CASCADE;'))

        summary = []

        print("📦 正在导入业务表数据...")
        for t_name in tables_to_sync:
            sqlite_table = sqlite_meta.tables[t_name]
            pg_table = pg_meta.tables[t_name]

            with sqlite_engine.connect() as s_conn:
                s_rows = s_conn.execute(sqlite_table.select()).mappings().all()

            if not s_rows:
                continue

            pg_cols = {col.name: col.type for col in pg_table.columns}

            processed_rows = []
            for row in s_rows:
                new_row = {}
                for k, v in row.items():
                    if k in pg_cols:
                        new_row[k] = convert_value(v, pg_cols[k])
                processed_rows.append(new_row)

            if processed_rows:
                pg_conn.execute(pg_table.insert(), processed_rows)
                summary.append((t_name, len(processed_rows)))

        # 确保仿真环境默认管理员可使用指定密码登录
        import bcrypt
        admin_pwd = "K9#mX2_vL8!qZ5*wR7"
        hashed = bcrypt.hashpw(admin_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        pg_conn.execute(
            text("UPDATE users SET hashed_password = :h WHERE username = :u;"),
            {"h": hashed, "u": "admin"}
        )

        # 恢复外键检查
        pg_conn.execute(text("SET session_replication_role = 'origin';"))

    print("\n✅ 数据同步完成！同步统计：")
    for t_name, count in sorted(summary, key=lambda x: x[1], reverse=True):
        print(f"  • {t_name.ljust(26)}: {count} 条记录")

if __name__ == "__main__":
    run_sync()

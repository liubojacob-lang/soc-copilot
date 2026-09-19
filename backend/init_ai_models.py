#!/usr/bin/env python3
"""Initialize and seed AI models in the database."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal, engine


def get_default_models_list() -> list[dict]:
    """Get the curated list of recommended models."""
    models: list[dict] = [
        # 1. 智能自动分配模式
        {
            "id": "auto",
            "provider": "auto",
            "display_name": "⚡ Auto 智能自动分配",
            "description": "根据提问长度、日志代码复杂度与安全推演场景，毫秒级动态路由至最优大模型",
            "enabled": True,
            "is_default": True,
            "capabilities": {"chat": True, "json": True, "tools": True, "auto": True},
            "max_tokens": 200000,
        },
        # 2. NVIDIA NIM - 极速日常研判与视觉多模态
        {
            "id": "meta/llama-3.2-11b-vision-instruct",
            "provider": "nvidia",
            "display_name": "Llama 3.2 11B Vision (NVIDIA)",
            "description": "Meta 快速多模态大模型，由 NVIDIA NIM 托管加速，毫秒级极速响应，适合日常安全问答与常规研判",
            "enabled": True,
            "is_default": False,
            "capabilities": {"chat": True, "json": True, "vision": True, "tools": True},
            "max_tokens": 131072,
        },
        # 3. NVIDIA NIM - 深度安全推演与思维链推理
        {
            "id": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "provider": "nvidia",
            "display_name": "Nemotron 3.5 Lightning 30B (NVIDIA)",
            "description": "NVIDIA 官方旗舰推理大模型，具备深度安全推演、APT 攻击链梳理与思维链反思能力",
            "enabled": True,
            "is_default": False,
            "capabilities": {"chat": True, "json": True, "tools": True},
            "max_tokens": 131072,
        },
        # 4. 智谱 AI - 200K 超长上下文日志与代码分析
        {
            "id": "glm-4.7-flash",
            "provider": "zhipu",
            "display_name": "智谱 GLM-4.7 Flash (免费)",
            "description": "智谱AI最新 MoE 架构免费大模型，200K 超长上下文，海量日志审计与复杂脚本反混淆首选",
            "enabled": True,
            "is_default": False,
            "capabilities": {"chat": True, "json": True, "tools": True},
            "max_tokens": 200000,
        },
    ]

    return models


async def seed_ai_models(session: AsyncSession) -> tuple[int, int]:
    """Seed or update AI models in the given database session.

    Returns:
        tuple[int, int]: (added_count, updated_count)
    """
    # 1. Ensure table exists
    await session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS ai_models (
            id VARCHAR(100) PRIMARY KEY,
            provider VARCHAR(50) NOT NULL,
            display_name VARCHAR(200) NOT NULL,
            description TEXT,
            enabled BOOLEAN DEFAULT TRUE NOT NULL,
            is_default BOOLEAN DEFAULT FALSE NOT NULL,
            capabilities JSON,
            max_tokens INTEGER,
            config JSON,
            created_at VARCHAR(30) NOT NULL,
            updated_at VARCHAR(30) NOT NULL
        )
        """
        )
    )

    await session.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS ai_user_settings (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL UNIQUE,
            default_model_id VARCHAR(100),
            created_at VARCHAR(30) NOT NULL,
            updated_at VARCHAR(30) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
        )
    )

    await session.execute(
        text(
            """
        CREATE INDEX IF NOT EXISTS ai_models_provider_enabled ON ai_models (provider, enabled)
        """
        )
    )

    now = datetime.now().isoformat()
    models_to_add = get_default_models_list()
    added_count = 0
    updated_count = 0

    for model in models_to_add:
        result = await session.execute(
            text("SELECT id, is_default FROM ai_models WHERE id = :id"),
            {"id": model["id"]},
        )
        existing = result.first()

        if existing:
            await session.execute(
                text(
                    """
                UPDATE ai_models
                SET display_name = :display_name,
                    description = :description,
                    enabled = :enabled,
                    capabilities = :capabilities,
                    max_tokens = :max_tokens,
                    updated_at = :updated_at
                WHERE id = :id
                """
                ),
                {
                    "id": model["id"],
                    "display_name": model["display_name"],
                    "description": model["description"],
                    "enabled": model["enabled"],
                    "capabilities": json.dumps(model["capabilities"]),
                    "max_tokens": model["max_tokens"],
                    "updated_at": now,
                },
            )
            updated_count += 1
        else:
            model_data = {
                **model,
                "capabilities": json.dumps(model["capabilities"]),
                "config": None,
                "created_at": now,
                "updated_at": now,
            }
            await session.execute(
                text(
                    """
                INSERT INTO ai_models
                (id, provider, display_name, description, enabled, is_default, capabilities, max_tokens, config, created_at, updated_at)
                VALUES
                (:id, :provider, :display_name, :description, :enabled, :is_default, :capabilities, :max_tokens, :config, :created_at, :updated_at)
                """
                ),
                model_data,
            )
            added_count += 1

    # v0.9.2: upsert-only seeding. The previous DELETE wiped admin-created
    # custom models on every startup, so it is gone. User settings pointing
    # at models that no longer exist are reset to 'auto' below.

    # Ensure 'auto' is marked as default
    await session.execute(
        text("UPDATE ai_models SET is_default = FALSE")
    )
    await session.execute(
        text("UPDATE ai_models SET is_default = TRUE WHERE id = 'auto'")
    )

    # Reset user settings only when the referenced model no longer exists;
    # choices pointing at custom models are preserved.
    await session.execute(
        text(
            "UPDATE ai_user_settings SET default_model_id = 'auto' "
            "WHERE default_model_id IS NOT NULL AND default_model_id != 'auto' "
            "AND default_model_id NOT IN (SELECT id FROM ai_models)"
        )
    )

    await session.commit()
    return added_count, updated_count


async def init_ai_models():
    """Main CLI entrypoint to initialize AI models."""
    print("🚀 Initializing AI models in database...")
    async with AsyncSessionLocal() as session:
        added, updated = await seed_ai_models(session)
        print(f"✅ AI models seeded successfully: {added} added, {updated} updated")

        result = await session.execute(
            text(
                "SELECT provider, display_name, id, enabled, is_default FROM ai_models ORDER BY provider, display_name"
            )
        )
        print("\nConfigured Models:")
        for row in result:
            status = "✓" if row[3] else "✗"
            default_tag = " [DEFAULT]" if row[4] else ""
            print(f"  {status} {row[1]} ({row[0]} - {row[2]}){default_tag}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_ai_models())

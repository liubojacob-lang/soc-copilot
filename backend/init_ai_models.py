#!/usr/bin/env python3
"""Initialize AI models in database."""

import asyncio
import sys
import json
from datetime import datetime
sys.path.insert(0, '/Users/levent/Desktop/sec/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.config import settings


async def init_ai_models():
    """Initialize AI model tables and add models."""

    # Use correct database path
    database_url = "sqlite+aiosqlite:////Users/levent/Desktop/sec/data/app.db"
    engine = create_async_engine(
        database_url,
        echo=False,
    )

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Create tables
        print("Creating AI model tables...")

        # Create ai_models table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_models (
                id VARCHAR(100) PRIMARY KEY,
                provider VARCHAR(50) NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                description TEXT,
                enabled BOOLEAN DEFAULT 1 NOT NULL,
                is_default BOOLEAN DEFAULT 0 NOT NULL,
                capabilities JSON,
                max_tokens INTEGER,
                config JSON,
                created_at VARCHAR(30) NOT NULL,
                updated_at VARCHAR(30) NOT NULL
            )
        """))

        # Create ai_user_settings table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_user_settings (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL UNIQUE,
                default_model_id VARCHAR(100),
                created_at VARCHAR(30) NOT NULL,
                updated_at VARCHAR(30) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """))

        # Create index for provider + enabled
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ai_models_provider_enabled ON ai_models (provider, enabled)
        """))

        await session.commit()
        print("✓ Tables created successfully")

        # Define models to add
        models_to_add = []

        # 智谱AI 模型
        if settings.zhipu_api_key:
            models_to_add.extend([
                {
                    "id": "glm-4",
                    "provider": "zhipu",
                    "display_name": "智谱 GLM-4",
                    "description": "智谱AI旗舰模型，支持长上下文理解和复杂推理",
                    "enabled": True,
                    "is_default": True,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 128000,
                },
                {
                    "id": "glm-4-plus",
                    "provider": "zhipu",
                    "display_name": "智谱 GLM-4 Plus",
                    "description": "智谱AI增强版模型，性能更强",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 128000,
                },
                {
                    "id": "glm-4-air",
                    "provider": "zhipu",
                    "display_name": "智谱 GLM-4 Air",
                    "description": "智谱AI轻量级模型，响应速度快",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 128000,
                },
            ])
            print(f"✓ 智谱API密钥已配置，添加 {len([m for m in models_to_add if m['provider'] == 'zhipu'])} 个智谱模型")

        # OpenRouter 模型（已移除 Kimi，改用 NVIDIA）
        if settings.openrouter_api_key:
            print(f"✓ OpenRouter API密钥已配置，但Kimi模型已移至NVIDIA")

        # NVIDIA 模型
        if settings.nvidia_api_key:
            models_to_add.extend([
                {
                    "id": "meta/llama-3.1-405b-instruct",
                    "provider": "nvidia",
                    "display_name": "Llama 3.1 405B (NVIDIA)",
                    "description": "Meta Llama 3.1 405B 指令模型，由NVIDIA托管",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 131072,
                },
                {
                    "id": "minimaxai/minimax-m2.1",
                    "provider": "nvidia",
                    "display_name": "MiniMax M2.1 (NVIDIA)",
                    "description": "MiniMax M2.1 模型，由NVIDIA托管",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 8192,
                },
                {
                    "id": "moonshotai/kimi-k2.5",
                    "provider": "nvidia",
                    "display_name": "Kimi K2.5 (NVIDIA)",
                    "description": "Moonshot AI Kimi K2.5 模型，由NVIDIA托管",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 131072,
                },
            ])
            print(f"✓ NVIDIA API密钥已配置，添加 {len([m for m in models_to_add if m['provider'] == 'nvidia'])} 个NVIDIA模型")

        # Anthropic 模型
        if settings.anthropic_api_key:
            models_to_add.extend([
                {
                    "id": "claude-3-5-sonnet-20241022",
                    "provider": "anthropic",
                    "display_name": "Claude 3.5 Sonnet",
                    "description": "Anthropic Claude 3.5 Sonnet - 最新高性能模型",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "vision": True, "tools": True},
                    "max_tokens": 200000,
                },
            ])
            print(f"✓ Anthropic API密钥已配置，添加 {len([m for m in models_to_add if m['provider'] == 'anthropic'])} 个Claude模型")

        # OpenAI 模型
        if settings.openai_api_key:
            models_to_add.extend([
                {
                    "id": "gpt-4o",
                    "provider": "openai",
                    "display_name": "GPT-4o",
                    "description": "OpenAI GPT-4o 多模态模型",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "vision": True, "tools": True},
                    "max_tokens": 128000,
                },
                {
                    "id": "gpt-4o-mini",
                    "provider": "openai",
                    "display_name": "GPT-4o Mini",
                    "description": "OpenAI GPT-4o Mini 经济高效模型",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "vision": True, "tools": True},
                    "max_tokens": 128000,
                },
            ])
            print(f"✓ OpenAI API密钥已配置，添加 {len([m for m in models_to_add if m['provider'] == 'openai'])} 个OpenAI模型")

        # Moonshot 模型
        if settings.moonshot_api_key:
            models_to_add.extend([
                {
                    "id": "moonshot-v1-8k",
                    "provider": "moonshot",
                    "display_name": "Moonshot v1 8K",
                    "description": "Moonshot AI 中文优化模型",
                    "enabled": True,
                    "is_default": False,
                    "capabilities": {"chat": True, "json": True, "tools": True},
                    "max_tokens": 8192,
                },
            ])
            print(f"✓ Moonshot API密钥已配置，添加 {len([m for m in models_to_add if m['provider'] == 'moonshot'])} 个Moonshot模型")

        # Insert models
        now = datetime.now().isoformat()
        added_count = 0
        updated_count = 0

        for model in models_to_add:
            # Check if model exists
            result = await session.execute(
                text("SELECT id FROM ai_models WHERE id = :id"),
                {"id": model["id"]}
            )
            existing = result.first()

            if existing:
                # Update existing model
                await session.execute(text("""
                    UPDATE ai_models
                    SET display_name = :display_name,
                        description = :description,
                        enabled = :enabled,
                        is_default = :is_default,
                        capabilities = :capabilities,
                        max_tokens = :max_tokens,
                        updated_at = :updated_at
                    WHERE id = :id
                """), {
                    "id": model["id"],
                    "display_name": model["display_name"],
                    "description": model["description"],
                    "enabled": model["enabled"],
                    "is_default": model["is_default"],
                    "capabilities": json.dumps(model["capabilities"]),
                    "max_tokens": model["max_tokens"],
                    "updated_at": now,
                })
                updated_count += 1
            else:
                # Insert new model with timestamps
                model_data = {
                    **model,
                    "capabilities": json.dumps(model["capabilities"]),
                    "created_at": now,
                    "updated_at": now,
                }
                await session.execute(text("""
                    INSERT INTO ai_models
                    (id, provider, display_name, description, enabled, is_default, capabilities, max_tokens, created_at, updated_at)
                    VALUES
                    (:id, :provider, :display_name, :description, :enabled, :is_default, :capabilities, :max_tokens, :created_at, :updated_at)
                """), model_data)
                added_count += 1

        await session.commit()

        print(f"\n✅ 初始化完成!")
        print(f"   新增模型: {added_count}")
        print(f"   更新模型: {updated_count}")
        print(f"   总计模型: {len(models_to_add)}")

        # List all models
        result = await session.execute(text("""
            SELECT provider, display_name, enabled FROM ai_models ORDER BY provider, display_name
        """))
        print(f"\n当前已配置的模型:")
        for row in result:
            status = "✓" if row[2] else "✗"
            print(f"  {status} {row[1]} ({row[0]})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_ai_models())

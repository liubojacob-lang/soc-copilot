"""Seed the prompt registry with the builtin runtime templates (T3.2).

Upserts the four production prompt templates as active ``v1`` rows in the
dev and staging environments so operators can hot-edit them from the
Prompt Registry admin API instead of redeploying code.

Usage:
    cd backend && python -m scripts.seed_prompt_registry [--env dev,staging] [--dry-run]

Prod rows are deliberately NOT seeded: promoting a prompt to prod is an
explicit operator action (copy the dev row, bump version, activate).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from db.session import AsyncSessionLocal
from models.prompt_registry import PromptEnvironment, PromptRegistryModel
from services.alerting.alert_service import _ALERT_USER_PROMPT_BUILTIN
from services.lifecycle.alert_pipeline_service import _TRIAGE_PROMPT_TEMPLATE
from services.report_service import _REPORT_USER_PROMPT_BUILTIN
from services.timeline_service import _TIMELINE_USER_PROMPT_BUILTIN

# name → (builtin template, description)
BUILTIN_PROMPTS: dict[str, tuple[str, str]] = {
    "alert_analysis_user": (
        _ALERT_USER_PROMPT_BUILTIN,
        "Alert deep-analysis user prompt (placeholders: raw_log, ips_str, "
        "domains_str, urls_str, hashes_str)",
    ),
    "alert_triage": (
        _TRIAGE_PROMPT_TEMPLATE,
        "Auto-pipeline triage prompt (placeholder: alert_block; JSON braces "
        "must stay doubled)",
    ),
    "report_generation": (
        _REPORT_USER_PROMPT_BUILTIN,
        "Report generation user prompt (placeholders: alert_json, notes_text)",
    ),
    "timeline_reconstruction": (
        _TIMELINE_USER_PROMPT_BUILTIN,
        "Timeline reconstruction user prompt (placeholders: type_hint, "
        "raw_log, ips_str, domains_str, urls_str, hashes_str)",
    ),
}

VERSION = "v1"


async def seed(environments: list[str], dry_run: bool = False) -> dict[str, int]:
    """Idempotently upsert builtin prompts. Returns per-env counters."""
    stats: dict[str, int] = {}
    async with AsyncSessionLocal() as session:
        for env in environments:
            created = updated = 0
            for name, (content, description) in BUILTIN_PROMPTS.items():
                stmt = select(PromptRegistryModel).where(
                    PromptRegistryModel.name == name,
                    PromptRegistryModel.version == VERSION,
                    PromptRegistryModel.environment == env,
                )
                row = (await session.execute(stmt)).scalar_one_or_none()
                if row is None:
                    # Deactivate any other active version first (one active
                    # per name+env is enforced logically; the unique
                    # constraint covers name+version+env).
                    session.add(
                        PromptRegistryModel(
                            name=name,
                            version=VERSION,
                            content=content,
                            variables={"description": description},
                            environment=env,
                            is_active=True,
                        )
                    )
                    created += 1
                else:
                    row.content = content
                    row.is_active = True
                    updated += 1
            stats[env] = created + updated
            if not dry_run:
                await session.commit()
            print(
                f"[{env}] created={created} updated={updated}"
                + (" (dry-run, not committed)" if dry_run else "")
            )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        default="dev,staging",
        help="Comma-separated registry environments (default: dev,staging)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    environments = [e.strip() for e in args.env.split(",") if e.strip()]
    for env in environments:
        if env not in [e.value for e in PromptEnvironment]:
            raise SystemExit(f"Unknown environment: {env!r}")

    asyncio.run(seed(environments, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

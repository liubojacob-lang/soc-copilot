"""Runtime prompt resolution against the prompt_registry table (T3.2).

The prompt_registry has full CRUD/versioning but was previously never
consumed: production prompts were hardcoded in each service, so changing a
prompt required a code deploy. This module closes that gap:

    template = await resolve_prompt("alert_analysis_user", BUILTIN_TEMPLATE)

Resolution rules:

- Looks up the ACTIVE version of ``(name, <mapped environment>)``.
- Falls back to the caller's builtin template on ANY miss or error — the
  registry must never break the analysis path.
- Environment mapping: development/test → dev, staging → staging,
  production → prod (registry enum).

Templates use ``str.format`` placeholders only; registry overrides must keep
the same placeholders, which the seed script guarantees for the builtins.
"""

from sqlalchemy import select

from core.config import settings
from core.logger import get_logger
from models.prompt_registry import PromptEnvironment, PromptRegistryModel

logger = get_logger(__name__)

_ENV_MAPPING = {
    "development": PromptEnvironment.DEV,
    "test": PromptEnvironment.DEV,
    "staging": PromptEnvironment.STAGING,
    "production": PromptEnvironment.PROD,
}


def _registry_environment() -> PromptEnvironment:
    return _ENV_MAPPING.get(settings.environment, PromptEnvironment.DEV)


async def resolve_prompt(
    name: str,
    builtin: str,
    session_factory=None,
) -> str:
    """Return the active registry content for ``name``, or ``builtin``.

    Args:
        name: Registry prompt name (e.g. "alert_analysis_user").
        builtin: Fallback template compiled into the code.
        session_factory: Optional async session factory (injectable for
            tests); defaults to the app's AsyncSessionLocal.

    Returns:
        The resolved template string. NEVER raises.
    """
    if session_factory is None:
        from db.session import AsyncSessionLocal

        session_factory = AsyncSessionLocal

    environment = _registry_environment()
    try:
        async with session_factory() as session:
            stmt = (
                select(PromptRegistryModel)
                .where(
                    PromptRegistryModel.name == name,
                    PromptRegistryModel.environment == environment.value,
                    PromptRegistryModel.is_active.is_(True),
                )
                .order_by(PromptRegistryModel.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None or not row.content or not row.content.strip():
                return builtin
            logger.debug(
                f"Prompt '{name}' resolved from registry "
                f"(v{row.version}, {environment.value})"
            )
            return row.content
    except Exception as e:  # registry outage must not take down analysis
        logger.warning(
            f"Prompt registry lookup failed for '{name}', using builtin: {e!s}"
        )
        return builtin

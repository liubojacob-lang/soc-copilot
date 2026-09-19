"""Import Phishing IOC Auto-Response playbook."""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.playbook_definition import PlaybookDefinitionModel
from services.playbook.playbook_dag_compiler import DAGCompiler, DAGValidationError

# Database path (same as session.py)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"


async def import_playbook():
    """Import the phishing playbook."""
    # Load playbook JSON
    playbook_path = (
        Path(__file__).parent.parent / "data" / "phishing_ioc_response_playbook.json"
    )

    if not playbook_path.exists():
        print(f"ERROR: Playbook file not found: {playbook_path}")
        return False

    with open(playbook_path, encoding="utf-8") as f:
        playbook_data = json.load(f)

    print(f"Loading playbook: {playbook_data['name']}")

    # Validate DAG
    try:
        compiled = await DAGCompiler.validate_and_compile(playbook_data["dag"])
        print(
            f"OK: DAG validation passed: {compiled['node_count']} nodes, {compiled['edge_count']} edges"
        )
    except DAGValidationError as e:
        print(f"ERROR: DAG validation failed: {e}")
        return False

    # Create database session
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Import and initialize database
    import sys

    sys.path.insert(0, str(backend_dir))
    from db.session import init_db

    await init_db()

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Check if playbook already exists
        result = await session.execute(
            select(PlaybookDefinitionModel).where(
                PlaybookDefinitionModel.name == playbook_data["name"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(
                f"WARNING: Playbook '{playbook_data['name']}' already exists (ID: {existing.id})"
            )
            print("   Use the UI to update or delete it first.")
            return True

        # Create new playbook
        definition = PlaybookDefinitionModel(
            name=playbook_data["name"],
            description=playbook_data["description"],
            version=playbook_data["version"],
            definition_json=playbook_data["dag"],
            is_active=playbook_data["is_active"],
        )

        session.add(definition)
        await session.commit()

        print("SUCCESS: Playbook imported successfully!")
        print(f"   ID: {definition.id}")
        print(f"   Name: {definition.name}")
        print(f"   Version: {definition.version}")
        print(f"   Nodes: {len(playbook_data['dag']['nodes'])}")
        print(f"   Edges: {len(playbook_data['dag']['edges'])}")

    await engine.dispose()
    return True


if __name__ == "__main__":
    print(">>> Importing Phishing IOC Auto-Response Playbook...")
    print("-" * 60)

    success = asyncio.run(import_playbook())

    print("-" * 60)
    if success:
        print("SUCCESS: Import complete!")
        print("\nTo run this playbook:")
        print("   1. Go to http://localhost:8080/playbooks/definitions")
        print("   2. Find Phishing IOC Auto-Response")
        print("   3. Click Run with input:")
        print("      {")
        print('        "case_id": "CASE-2026-0001",')
        print('        "ioc": "evil-example.com",')
        print('        "ioc_type": "domain",')
        print('        "alert_source": "email-gateway",')
        print('        "severity": "high",')
        print('        "reporter": "soc@company.com"')
        print("      }")
    else:
        print("ERROR: Import failed!")
        sys.exit(1)

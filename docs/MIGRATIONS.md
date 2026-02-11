# Database Migrations Guide

## Overview

SOC Copilot uses **Alembic** for database schema migrations. Migrations are automatically run on application startup.

## Directory Structure

```
backend/
├── alembic.ini              # Alembic configuration
├── migrate.py               # Migration helper script
├── migrations/              # Old SQL migrations (deprecated)
├── migrations_alembic/      # Alembic migrations
│   ├── env.py              # Migration environment configuration
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration scripts
│       └── 475ad8e8fb9b_initial_migration.py
└── models/                 # SQLAlchemy models
```

## Automatic Migration on Startup

Migrations are automatically run when the application starts. No manual intervention needed.

## Manual Migration Commands

### Run all pending migrations
```bash
cd backend
source venv/Scripts/activate  # Windows
# source venv/bin/activate     # Linux/Mac
python migrate.py
```

### Using Alembic directly
```bash
cd backend
source venv/Scripts/activate

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
source venv/Scripts/activate
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

### Missing migration table
```bash
alembic stamp head
```

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

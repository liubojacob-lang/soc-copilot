"""
Database Index Optimization
Add composite indexes for common query patterns to improve performance
"""

from sqlalchemy import Index
from db.session import Base


def create_composite_indexes():
    """
    Create composite indexes for performance optimization

    Composite indexes improve query performance for:
    - Multi-column WHERE clauses
    - ORDER BY with WHERE clauses
    - JOIN operations
    """

    # Import models
    from models.playbook_definition import PlaybookDefinitionModel
    from models.playbook_run import PlaybookRunModel
    from models.user import UserModel
    from models.alert import AlertModel

    indexes = []

    # 1. Playbook runs: status + created_at (for listing runs)
    # Common query: SELECT * FROM playbook_runs WHERE status = ? ORDER BY created_at DESC
    indexes.append(
        Index(
            'idx_playbook_run_status_time',
            PlaybookRunModel.status,
            PlaybookRunModel.started_at.desc()
        )
    )

    # 2. Playbook runs: definition_id + created_at
    # Common query: SELECT * FROM playbook_runs WHERE definition_id = ? ORDER BY created_at DESC
    indexes.append(
        Index(
            'idx_playbook_run_def_time',
            PlaybookRunModel.definition_id,
            PlaybookRunModel.created_at.desc()
        )
    )

    # 3. Playbook definitions: is_active + updated_at
    # Common query: SELECT * FROM playbook_definitions WHERE is_active = true ORDER BY updated_at DESC
    indexes.append(
        Index(
            'idx_playbook_def_active_time',
            PlaybookDefinitionModel.is_active,
            PlaybookDefinitionModel.updated_at.desc()
        )
    )

    # 4. Playbook definitions: status + published_at
    # Common query: SELECT * FROM playbook_definitions WHERE status = 'published' ORDER BY published_at DESC
    indexes.append(
        Index(
            'idx_playbook_def_status_published',
            PlaybookDefinitionModel.status,
            PlaybookDefinitionModel.published_at.desc()
        )
    )

    # 5. Users: role + is_active
    # Common query: SELECT * FROM users WHERE role = ? AND is_active = true
    indexes.append(
        Index(
            'idx_user_role_active',
            UserModel.role,
            UserModel.is_active
        )
    )

    # 6. Users: is_active + created_at (for listing active users)
    # Common query: SELECT * FROM users WHERE is_active = true ORDER BY created_at DESC
    indexes.append(
        Index(
            'idx_user_active_time',
            UserModel.is_active,
            UserModel.created_at.desc()
        )
    )

    # 7. Alerts: severity + created_at
    # Common query: SELECT * FROM alerts WHERE severity >= ? ORDER BY created_at DESC
    indexes.append(
        Index(
            'idx_alert_severity_time',
            AlertModel.severity,
            AlertModel.created_at.desc()
        )
    )

    # 8. Alerts: status + created_at
    # Common query: SELECT * FROM alerts WHERE status = 'open' ORDER BY created_at DESC
    indexes.append(
        Index(
            'idx_alert_status_time',
            AlertModel.status,
            AlertModel.created_at.desc()
        )
    )

    # Create indexes
    for index in indexes:
        try:
            index.create(bind=Base.metadata.bind, checkfirst=True)
            print(f"Created index: {index.name}")
        except Exception as e:
            print(f"Error creating index {index.name}: {e}")


# Index name constants for reference
class IndexNames:
    """Database index names"""

    # Playbook runs
    PLAYBOOK_RUN_STATUS_TIME = 'idx_playbook_run_status_time'
    PLAYBOOK_RUN_DEF_TIME = 'idx_playbook_run_def_time'

    # Playbook definitions
    PLAYBOOK_DEF_ACTIVE_TIME = 'idx_playbook_def_active_time'
    PLAYBOOK_DEF_STATUS_PUBLISHED = 'idx_playbook_def_status_published'

    # Users
    USER_ROLE_ACTIVE = 'idx_user_role_active'
    USER_ACTIVE_TIME = 'idx_user_active_time'

    # Alerts
    ALERT_SEVERITY_TIME = 'idx_alert_severity_time'
    ALERT_STATUS_TIME = 'idx_alert_status_time'


if __name__ == "__main__":
    """Test index creation"""
    print("Creating composite indexes...")
    create_composite_indexes()
    print("Index creation complete!")

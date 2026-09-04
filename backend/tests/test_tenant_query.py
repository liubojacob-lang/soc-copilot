from sqlalchemy import select
from models.security_alert import SecurityAlert
from services.tenant_query import with_tenant_scope, redis_tenant_key

def test_redis_tenant_key():
    assert redis_tenant_key("tenant-1", "cache_key") == "tenant:tenant-1:cache_key"

def test_with_tenant_scope_applied():
    q = select(SecurityAlert)
    scoped_q = with_tenant_scope(q, SecurityAlert, "org-abc")
    assert "tenant_id = :tenant_id_1" in str(scoped_q)

def test_with_tenant_scope_model_without_tenant():
    class DummyNoTenant:
        pass
    q = select(SecurityAlert)
    scoped_q = with_tenant_scope(q, DummyNoTenant, "org-abc")
    assert scoped_q == q

"""Tests for Cloud Native & Container Security Router."""

import pytest


@pytest.mark.asyncio
async def test_cloud_native_dashboard(auth_client):
    """Test getting cloud native security dashboard metrics."""
    resp = await auth_client.get("/api/v1/cloud-native/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data or "overview" in data or "total_containers" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_cloud_native_compliance_report(auth_client):
    """Test getting compliance report."""
    resp = await auth_client.get("/api/v1/cloud-native/compliance/report")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict | list)


@pytest.mark.asyncio
async def test_cloud_native_connections(auth_client):
    """Test listing cloud connections."""
    resp = await auth_client.get("/api/v1/cloud-native/cloud/connections")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict | list)


@pytest.mark.asyncio
async def test_cloud_native_falco_stats(auth_client):
    """Test getting Falco runtime alert statistics."""
    resp = await auth_client.get("/api/v1/cloud-native/falco-alerts/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_container_scan_request(auth_client):
    """Test initiating a container image security scan."""
    payload = {"image": "nginx", "tag": "alpine"}
    resp = await auth_client.post("/api/v1/cloud-native/containers/scan", json=payload)
    assert resp.status_code in (200, 201, 202)


@pytest.mark.asyncio
async def test_k8s_scan_request(auth_client):
    """Test initiating a Kubernetes security scan."""
    payload = {"cluster_name": "k8s-prod-cluster", "namespace": "default"}
    resp = await auth_client.post("/api/v1/cloud-native/kubernetes/scan", json=payload)
    assert resp.status_code in (200, 201, 202)

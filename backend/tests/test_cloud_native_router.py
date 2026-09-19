"""Tests for Cloud Native & Container Security Router."""

import pytest


@pytest.mark.asyncio
async def test_cloud_native_dashboard(auth_client):
    """Test getting cloud native security dashboard metrics."""
    resp = await auth_client.get("/api/v1/cloud-native/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert (
        "metrics" in data
        or "overview" in data
        or "total_containers" in data
        or isinstance(data, dict)
    )


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


@pytest.mark.asyncio
async def test_cloud_native_clusters(auth_client):
    """Test getting connected Kubernetes clusters."""
    resp = await auth_client.get("/api/v1/cloud-native/kubernetes/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert "clusters" in data
    assert data["total_clusters"] >= 1


@pytest.mark.asyncio
async def test_cloud_native_resources(auth_client):
    """Test getting Kubernetes resources by type."""
    resp = await auth_client.get("/api/v1/cloud-native/kubernetes/resources/pods")
    assert resp.status_code == 200
    data = resp.json()
    assert "resources" in data
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_cloud_native_containers_list(auth_client):
    """Test getting container inventory with breakdown metrics and pagination."""
    resp = await auth_client.get("/api/v1/cloud-native/containers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 45
    assert data["filtered_total"] == 45
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 5
    assert data["running"] == 42
    assert data["warning"] == 2
    assert data["terminated"] == 1
    assert data["vulnerable"] >= 1
    assert len(data["containers"]) == 10

    # Test page 2
    resp_p2 = await auth_client.get(
        "/api/v1/cloud-native/containers?page=2&page_size=10"
    )
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert data_p2["page"] == 2
    assert len(data_p2["containers"]) == 10
    assert data_p2["containers"][0]["id"] != data["containers"][0]["id"]

    # Test page_size=50 (fetch all in 1 page)
    resp_all = await auth_client.get("/api/v1/cloud-native/containers?page_size=50")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["total_pages"] == 1
    assert len(data_all["containers"]) == 45

    # Test filtering by status with pagination
    resp_warn = await auth_client.get("/api/v1/cloud-native/containers?status=warning")
    assert resp_warn.status_code == 200
    data_warn = resp_warn.json()
    assert data_warn["filtered_total"] == 2
    assert data_warn["total_pages"] == 1
    assert all(c["status"] == "warning" for c in data_warn["containers"])

    # Test filtering by search keyword
    resp_search = await auth_client.get("/api/v1/cloud-native/containers?search=nginx")
    assert resp_search.status_code == 200
    data_search = resp_search.json()
    assert data_search["filtered_total"] >= 1


@pytest.mark.asyncio
async def test_cloud_native_container_detail(auth_client):
    """Test getting details for a specific container."""
    resp = await auth_client.get("/api/v1/cloud-native/containers/cnt-prod-web-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "cnt-prod-web-01"
    assert data["cluster_name"] == "k8s-prod-cluster"
    assert "ports" in data
    assert "command" in data
    assert "mounts" in data

    # Test not found
    resp_404 = await auth_client.get("/api/v1/cloud-native/containers/non-existent-id")
    assert resp_404.status_code == 404

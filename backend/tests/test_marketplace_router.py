"""Tests for Playbook Marketplace Router."""

import pytest


@pytest.mark.asyncio
async def test_marketplace_categories(auth_client):
    """Test getting marketplace categories."""
    resp = await auth_client.get("/api/v1/marketplace/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_marketplace_featured(auth_client):
    """Test getting featured marketplace playbooks."""
    resp = await auth_client.get("/api/v1/marketplace/featured")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_marketplace_trending(auth_client):
    """Test getting trending marketplace playbooks."""
    resp = await auth_client.get("/api/v1/marketplace/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_marketplace_dashboard(auth_client):
    """Test getting marketplace dashboard stats."""
    resp = await auth_client.get("/api/v1/marketplace/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_marketplace_list_playbooks(auth_client):
    """Test listing marketplace playbooks."""
    resp = await auth_client.get("/api/v1/marketplace/playbooks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "items" in data or "playbooks" in data or "total" in data


@pytest.mark.asyncio
async def test_marketplace_admin_stats(auth_client):
    """Test getting marketplace admin statistics."""
    resp = await auth_client.get("/api/v1/marketplace/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)

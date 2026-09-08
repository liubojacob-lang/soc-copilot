#!/usr/bin/env python3

import os

import requests

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]  # 必须由环境变量提供，不得硬编码

session = requests.Session()

# Login (sets HttpOnly cookies: access_token, refresh_token, csrf_token)
login_resp = session.post(
    "http://localhost:8000/api/auth/login",
    json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    timeout=30,
)
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code} - {login_resp.text}")
    exit(1)

csrf_token = login_resp.json().get("csrf_token")
access_token = session.cookies.get("access_token")
print(f"Logged in successfully! Token: {access_token[:30] if access_token else 'Cookie set'}...")

# Get models
headers = {}
if csrf_token:
    headers["X-CSRF-Token"] = csrf_token

models_resp = session.get(
    "http://localhost:8000/api/ai/models", headers=headers, timeout=30
)

data = models_resp.json()
models = data.get("models", [])
print(f"\nAI Models ({len(models)} total):")
for model in models:
    default_tag = " [DEFAULT]" if model.get("is_default") else ""
    print(f"  ✓ {model['display_name']} ({model['provider']}){default_tag}")
print(f"\nDefault: {data.get('default_model_id', 'None')}")

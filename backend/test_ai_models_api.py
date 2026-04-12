#!/usr/bin/env python3

import requests

# Login
login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin123!"},
)
token = login_resp.json().get("access_token")
print(f"Token: {token[:50]}...")

# Get models
headers = {"Authorization": f"Bearer {token}"}
models_resp = requests.get("http://localhost:8000/api/ai/models", headers=headers)

print(f"\nAI Models ({len(models_resp.json().get('models', []))} total):")
for model in models_resp.json().get("models", [])[:10]:
    print(f"  ✓ {model['display_name']} ({model['provider']})")
    if model.get("is_default"):
        print("   [DEFAULT]")
print(f"\nDefault: {models_resp.json().get('default_model_id', 'None')}")

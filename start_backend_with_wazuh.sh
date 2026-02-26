#!/bin/bash

# Export environment variables
export WAZUH_ENABLED=true
export WAZUH_API_URL=http://localhost:55000
export WAZUH_API_USERNAME=wazuh-wui
export WAZUH_API_PASSWORD=wazuh-ui-wazuh-wui
export WAZUH_VERIFY_SSL=false
export WAZUH_RECEIVER_ENABLED=true
export WAZUH_RECEIVER_AUTO_START=false
export REDIS_URL=redis://localhost:6379/0

# Change to backend directory
cd /Users/levent/Desktop/sec/backend

# Start backend
echo "Starting SOC Copilot backend with Wazuh integration..."
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

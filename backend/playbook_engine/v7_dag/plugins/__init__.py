"""Built-in node plugins for SOC Copilot v0.7.4.

This package contains the default node plugins that ship with SOC Copilot:

- builtin_http_request: HTTP request with hostname whitelist sandbox
- builtin_otx_lookup: OTX threat intelligence lookup
- builtin_decision: Conditional branching/logic
- builtin_slack_notify: Slack webhook notifications
- builtin_human_approval: Manual approval workflow

To add a new plugin:
1. Create a new file in this directory
2. Inherit from BaseNodePlugin
3. Implement the required properties and execute() method
4. The plugin will be auto-loaded on startup
"""

# Plugins are auto-loaded by NodeRegistry.auto_load_plugins()

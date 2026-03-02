================================================================================
Backend Error Code Migration Report
================================================================================

Total files with HTTPException: 29
Total HTTPException usages: 189

Breakdown by HTTP Status Code:
----------------------------------------
  400: 30
  403: 45
  404: 62
  422: 2
  500: 50

Suggested Error Code Mappings:
----------------------------------------
  GeneralError.INTERNAL_ERROR: 50
  ResourceError.NOT_FOUND: 45
  AuthError.FORBIDDEN: 36
  GeneralError.UNKNOWN_ERROR: 30
  AuthError.INSUFFICIENT_PERMISSIONS: 9
  DefinitionError.NOT_FOUND: 8
  TriggerError.NOT_FOUND: 7
  AuthError.USER_NOT_FOUND: 2
  ValidationError.INVALID_FORMAT: 2

================================================================================
Detailed File Analysis
================================================================================


/Users/levent/Desktop/sec/backend/app/api/v1/alerts/ingest.py
--------------------------------------------------------------------------------
  Line 130: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 167: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 185: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 190: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 242: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/dependencies/authorization.py
--------------------------------------------------------------------------------
  Line 96: status_code=403
    Message: 
    Suggested: AuthError.FORBIDDEN


/Users/levent/Desktop/sec/backend/middleware/authorization_middleware.py
--------------------------------------------------------------------------------
  Line 206: status_code=403
    Message: You do not have permission to access this resource
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS


/Users/levent/Desktop/sec/backend/routers/admin_settings.py
--------------------------------------------------------------------------------
  Line 103: status_code=403
    Message: Only administrators can view settings
    Suggested: AuthError.FORBIDDEN

  Line 128: status_code=403
    Message: Only administrators can update settings
    Suggested: AuthError.FORBIDDEN


/Users/levent/Desktop/sec/backend/routers/alert.py
--------------------------------------------------------------------------------
  Line 40: status_code=422
    Message: 
    Suggested: ValidationError.INVALID_FORMAT

  Line 43: status_code=500
    Message: Analysis failed
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/alert_enrichment.py
--------------------------------------------------------------------------------
  Line 48: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 64: status_code=400
    Message: Hours must be between 1 and 24
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 82: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 155: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/alerts_lifecycle.py
--------------------------------------------------------------------------------
  Line 50: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 68: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 86: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 104: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 122: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND

  Line 141: status_code=404
    Message: Alert not found
    Suggested: ResourceError.NOT_FOUND


/Users/levent/Desktop/sec/backend/routers/alerts_to_loki.py
--------------------------------------------------------------------------------
  Line 25: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 36: status_code=500
    Message: Failed to send test alert
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/assets.py
--------------------------------------------------------------------------------
  Line 35: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 59: status_code=404
    Message: Asset not found
    Suggested: ResourceError.NOT_FOUND

  Line 75: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 88: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND


/Users/levent/Desktop/sec/backend/routers/audit.py
--------------------------------------------------------------------------------
  Line 164: status_code=403
    Message: Permission denied
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS


/Users/levent/Desktop/sec/backend/routers/correlation.py
--------------------------------------------------------------------------------
  Line 139: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 207: status_code=404
    Message: Incident not found
    Suggested: ResourceError.NOT_FOUND

  Line 231: status_code=404
    Message: Incident not found
    Suggested: ResourceError.NOT_FOUND

  Line 236: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 341: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 358: status_code=404
    Message: Rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 362: status_code=403
    Message: Cannot update built-in rules
    Suggested: AuthError.FORBIDDEN

  Line 396: status_code=404
    Message: Rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 400: status_code=403
    Message: Cannot delete built-in rules
    Suggested: AuthError.FORBIDDEN

  Line 429: status_code=404
    Message: Rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 525: status_code=404
    Message: Rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 553: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/dify.py
--------------------------------------------------------------------------------
  Line 40: status_code=403
    Message: Only admins and analysts can list workflows
    Suggested: AuthError.FORBIDDEN

  Line 56: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 74: status_code=403
    Message: Only admins and analysts can view workflows
    Suggested: AuthError.FORBIDDEN

  Line 83: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 94: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 114: status_code=403
    Message: Only admins and analysts can execute workflows
    Suggested: AuthError.FORBIDDEN

  Line 135: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 155: status_code=403
    Message: Only admins can import workflows
    Suggested: AuthError.FORBIDDEN

  Line 162: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 205: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 225: status_code=403
    Message: Only admins and analysts can sync workflows
    Suggested: AuthError.FORBIDDEN

  Line 239: status_code=404
    Message: Definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 243: status_code=400
    Message: Definition is not linked to a Dify workflow
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 252: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 284: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 298: status_code=403
    Message: Only admins can view Dify config
    Suggested: AuthError.FORBIDDEN

  Line 352: status_code=403
    Message: Only admins can test connection
    Suggested: AuthError.FORBIDDEN

  Line 419: status_code=403
    Message: Only admins can delete imported workflows
    Suggested: AuthError.FORBIDDEN

  Line 432: status_code=404
    Message: Definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 437: status_code=400
    Message: Can only delete playbook definitions imported from Dify
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 459: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/ioc_hits.py
--------------------------------------------------------------------------------
  Line 28: status_code=400
    Message: IOC parameter is required
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 72: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/monitoring_alerts.py
--------------------------------------------------------------------------------
  Line 72: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 98: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 118: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 121: status_code=403
    Message: Access denied
    Suggested: AuthError.FORBIDDEN

  Line 129: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 151: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 154: status_code=403
    Message: Access denied
    Suggested: AuthError.FORBIDDEN

  Line 161: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 174: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 195: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 198: status_code=403
    Message: Access denied
    Suggested: AuthError.FORBIDDEN

  Line 204: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 214: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 237: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 259: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 281: status_code=404
    Message: Alert rule not found
    Suggested: ResourceError.NOT_FOUND

  Line 284: status_code=403
    Message: Access denied
    Suggested: AuthError.FORBIDDEN

  Line 307: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/notifications.py
--------------------------------------------------------------------------------
  Line 79: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 103: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/playbook/approvals.py
--------------------------------------------------------------------------------
  Line 151: status_code=403
    Message: Only admin and auditor roles can approve requests
    Suggested: AuthError.FORBIDDEN

  Line 164: status_code=404
    Message: Approval not found
    Suggested: ResourceError.NOT_FOUND

  Line 167: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 176: status_code=400
    Message: Approval has expired
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 245: status_code=403
    Message: Only admin and auditor roles can reject requests
    Suggested: AuthError.FORBIDDEN

  Line 258: status_code=404
    Message: Approval not found
    Suggested: ResourceError.NOT_FOUND

  Line 261: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 270: status_code=400
    Message: Approval has expired
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/playbook/definitions.py
--------------------------------------------------------------------------------
  Line 174: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 213: status_code=403
    Message: Playbook apply mode requires admin role
    Suggested: AuthError.FORBIDDEN

  Line 232: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 235: status_code=400
    Message: Definition is not active
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 317: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 321: status_code=403
    Message: Permission denied
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS


/Users/levent/Desktop/sec/backend/routers/playbook/runs.py
--------------------------------------------------------------------------------
  Line 54: status_code=403
    Message: Playbook apply mode requires admin role
    Suggested: AuthError.FORBIDDEN

  Line 149: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 154: status_code=403
    Message: Permission denied
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 186: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 191: status_code=403
    Message: Permission denied
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 224: status_code=403
    Message: Auditors cannot resume playbook runs
    Suggested: AuthError.FORBIDDEN

  Line 231: status_code=403
    Message: Playbook apply mode requires admin role
    Suggested: AuthError.FORBIDDEN

  Line 241: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 246: status_code=403
    Message: You can only resume your own runs
    Suggested: AuthError.FORBIDDEN

  Line 274: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/playbook/versions.py
--------------------------------------------------------------------------------
  Line 46: status_code=403
    Message: Only admin and analyst can publish definitions
    Suggested: AuthError.FORBIDDEN

  Line 86: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 113: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 132: status_code=403
    Message: Only admin and analyst can restore versions
    Suggested: AuthError.FORBIDDEN

  Line 173: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 204: status_code=403
    Message: Playbook replay with apply mode requires admin role
    Suggested: AuthError.FORBIDDEN

  Line 217: status_code=404
    Message: Run not found
    Suggested: ResourceError.NOT_FOUND

  Line 222: status_code=403
    Message: You can only replay your own runs
    Suggested: AuthError.FORBIDDEN

  Line 262: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 291: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 347: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 374: status_code=403
    Message: Only admin and analyst can import definitions
    Suggested: AuthError.FORBIDDEN

  Line 386: status_code=400
    Message: Content is required
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 423: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/playbook_definitions.py
--------------------------------------------------------------------------------
  Line 55: status_code=403
    Message: Insufficient permissions
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 63: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 154: status_code=404
    Message: Definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 180: status_code=403
    Message: Insufficient permissions
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 189: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 199: status_code=404
    Message: Definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 224: status_code=403
    Message: Only admins can delete definitions
    Suggested: AuthError.FORBIDDEN

  Line 230: status_code=404
    Message: Definition not found or has associated runs
    Suggested: DefinitionError.NOT_FOUND

  Line 564: status_code=404
    Message: Run not found
    Suggested: ResourceError.NOT_FOUND

  Line 605: status_code=404
    Message: Run not found
    Suggested: ResourceError.NOT_FOUND

  Line 636: status_code=403
    Message: Insufficient permissions
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 642: status_code=404
    Message: Run not found
    Suggested: ResourceError.NOT_FOUND

  Line 644: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/report.py
--------------------------------------------------------------------------------
  Line 43: status_code=500
    Message: Report generation failed
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/secrets.py
--------------------------------------------------------------------------------
  Line 90: status_code=403
    Message: Only admins can create secrets
    Suggested: AuthError.FORBIDDEN

  Line 97: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 133: status_code=403
    Message: Only admins can list secrets
    Suggested: AuthError.FORBIDDEN

  Line 163: status_code=403
    Message: Only admins can check key status
    Suggested: AuthError.FORBIDDEN

  Line 180: status_code=403
    Message: Only admins can view secrets
    Suggested: AuthError.FORBIDDEN

  Line 186: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 214: status_code=403
    Message: Only admins can update secrets
    Suggested: AuthError.FORBIDDEN

  Line 221: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 231: status_code=500
    Message: Failed to update secret
    Suggested: GeneralError.INTERNAL_ERROR

  Line 259: status_code=403
    Message: Only admins can delete secrets
    Suggested: AuthError.FORBIDDEN

  Line 265: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND


/Users/levent/Desktop/sec/backend/routers/security_alerts.py
--------------------------------------------------------------------------------
  Line 60: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 169: status_code=422
    Message: 
    Suggested: ValidationError.INVALID_FORMAT

  Line 173: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 248: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 264: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 272: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 298: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 327: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 405: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 424: status_code=404
    Message: 
    Suggested: ResourceError.NOT_FOUND

  Line 443: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/threat_intel.py
--------------------------------------------------------------------------------
  Line 38: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 63: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 89: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 189: status_code=400
    Message: Confirmation required
    Suggested: GeneralError.UNKNOWN_ERROR


/Users/levent/Desktop/sec/backend/routers/timeline.py
--------------------------------------------------------------------------------
  Line 40: status_code=500
    Message: Timeline build failed
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/triggers.py
--------------------------------------------------------------------------------
  Line 38: status_code=403
    Message: Permission denied
    Suggested: AuthError.INSUFFICIENT_PERMISSIONS

  Line 101: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 106: status_code=404
    Message: Associated playbook definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 135: status_code=404
    Message: Playbook definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 175: status_code=404
    Message: Playbook definition not found
    Suggested: DefinitionError.NOT_FOUND

  Line 188: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 217: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 224: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 236: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 262: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 278: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 281: status_code=400
    Message: Only webhook triggers can be tested
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 317: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND

  Line 319: status_code=400
    Message: Trigger is not a webhook trigger
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 344: status_code=404
    Message: Trigger not found
    Suggested: TriggerError.NOT_FOUND


/Users/levent/Desktop/sec/backend/routers/webhooks.py
--------------------------------------------------------------------------------
  Line 65: status_code=400
    Message: 
    Suggested: GeneralError.UNKNOWN_ERROR

  Line 68: status_code=500
    Message: Internal server error
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/websocket.py
--------------------------------------------------------------------------------
  Line 687: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 717: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


/Users/levent/Desktop/sec/backend/routers/websocket_filters.py
--------------------------------------------------------------------------------
  Line 127: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 179: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 198: status_code=404
    Message: No filters found for user
    Suggested: AuthError.USER_NOT_FOUND

  Line 208: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 234: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 253: status_code=404
    Message: No stats found for user
    Suggested: AuthError.USER_NOT_FOUND

  Line 263: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR

  Line 289: status_code=500
    Message: 
    Suggested: GeneralError.INTERNAL_ERROR


================================================================================
Migration Instructions
================================================================================


1. Import the new exception classes:
   from backend.core.exceptions import NotFoundException, UnauthorizedException
   from backend.core.enums.error_codes import DefinitionError, AuthError

2. Replace HTTPException with new exception classes:

   OLD:
       raise HTTPException(status_code=404, detail="Definition not found")

   NEW:
       raise NotFoundException(DefinitionError.NOT_FOUND)

3. For errors with additional details:

   OLD:
       raise HTTPException(
           status_code=404,
           detail=f"Definition {definition_id} not found"
       )

   NEW:
       raise NotFoundException(
           DefinitionError.NOT_FOUND,
           details={"definition_id": definition_id}
       )

4. Run tests to verify all changes

5. Update frontend error handling:
   - Error responses now include "code" field
   - Use t(`errors.${error.code}`) for localized messages

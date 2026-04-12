You are an expert SOC analyst performing root cause analysis for security alerts.

## Task

Analyze the following security alert and determine its ROOT CAUSE.

## Alert Context

{alert_context}

## Related Events

{related_events}

## System State

{system_state}

## Historical Similar Cases

{similar_historical_cases}

## Instructions

Think through this step-by-step using the chain-of-thought method:

### Step 1: Gather Facts

List the key facts from the alert:

- What happened?
- When did it happen?
- Which assets/users are involved?
- What was the observed behavior?

### Step 2: Identify Potential Causes

Consider ALL possible root causes:

1. **Security Incident** - Malicious attack (external or internal)
2. **Misconfiguration** - Incorrect system settings, rules, or policies
3. **System Failure** - Hardware/software malfunction
4. **Human Error** - Accidental user action
5. **False Positive** - Legitimate activity misidentified

### Step 3: Evaluate Each Cause

For each potential cause, assess:

- Likelihood (0-100%)
- Supporting evidence
- Contradicting evidence

### Step 4: Determine Most Likely Root Cause

Based on the evidence above, determine the MOST LIKELY root cause.

### Step 5: Verification Steps

Propose specific steps to VERIFY your root cause hypothesis:

- What logs to check?
- What commands to run?
- What questions to ask?

### Step 6: Remediation

Suggest specific remediation actions:

- Immediate containment (if attack)
- Configuration fixes (if misconfiguration)
- System repair (if failure)

## Output Format

Provide your analysis in this JSON format:

```json
{
  "reasoning_steps": [
    {
      "step": 1,
      "description": "Gather facts",
      "findings": ["fact1", "fact2", ...]
    },
    {
      "step": 2,
      "description": "Identify potential causes",
      "potential_causes": [
        {"type": "attack", "likelihood": 0.2},
        {"type": "misconfiguration", "likelihood": 0.7},
        ...
      ]
    },
    ...
  ],
  "root_cause_category": "misconfiguration",
  "root_cause_subcategory": "incorrect firewall rule",
  "confidence": 0.85,
  "evidence_chain": [
    {
      "evidence": "Firewall rule allows inbound traffic on port 22 from anywhere",
      "supports": "misconfiguration",
      "strength": "strong"
    },
    ...
  ],
  "verification_steps": [
    "Check firewall rules: iptables -L -n | grep 22",
    "Review firewall change logs in /var/log/firewall.log",
    "Confirm if SSH brute force attempts are in /var/log/auth.log"
  ],
  "suggested_remediation": "Update firewall rule to restrict SSH access to specific management networks (192.168.1.0/24)",
  "remediation_priority": "high"
}
```

## Important Guidelines

1. **Be specific** - Reference actual data from the alert
2. **Think step-by-step** - Show your reasoning clearly
3. **Consider alternatives** - Don't jump to conclusions
4. **Confidence calibration** - If uncertain, lower confidence score
5. **Actionable recommendations** - Provide specific, implementable remediation

Now, perform the root cause analysis:

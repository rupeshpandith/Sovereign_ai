---
name: sovereignty-audit
description: Use this skill when implementing or verifying the zero-external-call proof for the SIH sovereign AI workbench.
---

# Sovereignty Audit Skill

## Purpose

Prove that the AI workbench runs locally and makes no external calls.

## Required Checks

- External API calls = 0
- Cloud LLM calls = 0
- External DNS requests = 0
- Local model calls logged
- Sandbox network disabled
- Firewall/network monitor visible
- Docker containers isolated where possible

## Demo Dashboard

Show:

```text
Internet Access: BLOCKED
External API Calls: 0
Cloud LLM Calls: 0
DNS Requests: 0
Local Model Calls: <count>
Documents Processed: <count>
Sandbox Executions: <count>
Data Residency: LOCAL

```

## Constraints
Do not fake sovereignty logs.
Do not rely only on app-level settings.
Prefer infrastructure-level blocking:
Docker network restrictions
firewall rules
disabled outbound network
packet capture proof
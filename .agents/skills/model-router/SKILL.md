---
name: model-router
description: Use this skill when implementing model auto-selection across local open-weight models for the SIH sovereign AI workbench.
---

# Model Router Skill

## Purpose

Implement task-aware routing across local open-weight models.

## Required Routing

- Coding/debugging → coding model
- Scanned document/image task → vision/OCR pipeline
- SOP/manual search → embedding model + reasoning model
- Simple summarization → small local text model
- Calculation verification → Python sandbox
- Approval note generation → reasoning/writing model

## Router Design

Use a model registry:

```yaml
models:
  coding:
    name: local-code-model
    endpoint: http://localhost:8001
  reasoning:
    name: local-reasoning-model
    endpoint: http://localhost:8002
  vision:
    name: local-vision-model
    endpoint: http://localhost:8003
  embedding:
    name: local-embedding-model
    endpoint: http://localhost:8004

```

## Required Logs

For every request log:

task type
selected model
reason for selection
fallback model if any
latency
success/failure
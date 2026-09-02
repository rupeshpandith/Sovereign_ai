---
name: sandbox-code-runner
description: Use this skill when building the local code execution sandbox for the SIH workbench.
---

# Sandbox Code Runner Skill

## Purpose

Run generated or uploaded code safely.

## Requirements

- No network access
- Restricted filesystem
- CPU/memory/time limits
- Temporary working directory
- Captured stdout/stderr
- Test execution support
- Logs visible in UI

## Do Not Allow

- arbitrary host shell access
- package installation during execution
- access to project secrets
- access to home directory
- internet access
- file deletion outside sandbox

## Recommended Implementation

Use Docker with:

```bash
--network none
--memory 512m
--cpus 1
--read-only

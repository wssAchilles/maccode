# TrafficPerceptionEngine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the answer-defense-focused foundation: project baseline, CV domain loop, advanced-B speed estimation, and demo JSON contract.

**Architecture:** Four layers are reserved from the start. Current implementation is intentionally concentrated in `shared`, `domain`, and `scripts`; `application`, `infrastructure`, and `interfaces` are package boundaries for Phase 3/4.

**Tech Stack:** Python 3.11+, NumPy, Pydantic Settings, pytest, Ruff, mypy. YOLO/supervision/OpenCV are optional runtime dependencies for real video inference.

---

## Milestones

- [ ] M1: Project baseline with `.venv`-based commands, shared settings, errors, schemas, and Makefile verification.
- [ ] M2: CV domain loop using injectable detection predictions, lightweight IOU tracking, LineZone-style crossing, and FrameReport aggregation.
- [ ] M3: Advanced-B speed estimation using DLT/SVD homography, RMSE validation, deterministic smoothing, and speed filters.
- [ ] M4: Demo report script exporting the frozen `FrameReport` contract for later FastAPI/WebSocket/React integration.

## Verification

- `make lint`
- `make typecheck`
- `make test`
- `make demo`

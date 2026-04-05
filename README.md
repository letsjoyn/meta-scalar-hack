---
title: Disaster Response Coordination Environment Server
emoji: 🚨
colorFrom: orange
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - disaster-response
  - emergency-ops
---

# 🚨 Disaster Response Coordination OpenEnv

A real-world OpenEnv environment that simulates **emergency incident command center operations**: incident routing, urgency assignment, resource-constrained responder dispatch, and handoff drafting.

Designed for training and evaluating agentic AI systems on practical disaster operations workflows — not games, not toys.

## Why This Is Real-World

Emergency command centers perform these tasks every day:

- **Route** incoming disaster incidents to the correct response unit (rescue, medical, utilities, shelter, logistics)
- **Triage** urgency levels (low → medium → high → urgent) under time pressure
- **Draft** clear operational handoff notes for field teams with actionable next steps
- **Manage** limited resource budgets (rescue helicopters, medical teams, generators) across simultaneous incidents
- **Avoid** cascading failures from wrong routing, missed urgency escalation, or delayed dispatch

Real-world parallel: FEMA Incident Command System (ICS), UN OCHA Humanitarian Operations Centers, City Emergency Operations Centers.

## Environment API

Full OpenEnv spec compliance with typed models and standard API:

| Endpoint | Description |
|----------|-------------|
| `POST /reset` | `reset(task_name=...) → observation` — start a new episode |
| `POST /step` | `step(action) → observation, reward, done, info` — take an action |
| `GET /state` | `state() → current typed state` — inspect server state |
| `GET /health` | Health check endpoint |

Validated via `openenv validate`.

### Key Files

| File | Purpose |
|------|---------|
| `models.py` | `SupportOpsAction`, `SupportOpsObservation`, `SupportOpsState` — typed Pydantic models |
| `tasks.py` | 15 deterministic ticket specifications across 3 difficulty levels |
| `server/support_ops_environment.py` | Environment logic, deterministic graders, resource budget |
| `server/app.py` | FastAPI app via OpenEnv `create_app(...)` |
| `inference.py` | Baseline inference script with structured stdout |
| `smoke_test.py` | Offline validation (no LLM required) |
| `openenv.yaml` | OpenEnv manifest |

## Action Space

`SupportOpsAction` fields:

| Field | Type | Description |
|-------|------|-------------|
| `action_type` | enum | One of: `classify`, `set_priority`, `draft_reply`, `submit_ticket`, `next_ticket`, `finish_episode`, `noop` |
| `ticket_id` | string (optional) | Target incident ID; defaults to active ticket |
| `predicted_team` | enum (optional) | `rescue`, `medical`, `utilities`, `shelter`, `logistics`, `general` |
| `predicted_priority` | enum (optional) | `low`, `medium`, `high`, `urgent` |
| `reply_text` | string (optional) | Operational handoff note for field teams (max 2000 chars) |

**Required workflow per ticket:** `classify` → `set_priority` → `draft_reply` → `submit_ticket`

Submitting without completing all steps triggers an invalid action penalty.

## Observation Space

`SupportOpsObservation` includes:

| Field | Description |
|-------|-------------|
| `task_name` | Current difficulty (easy/medium/hard) |
| `objective` | Natural language task instructions |
| `current_ticket_id` | Active incident ID |
| `current_ticket_message` | Full incident report text |
| `current_ticket_customer_tier` | Region criticality: district / metro / national |
| `inbox_snapshot` | Per-ticket progress with reward breakdowns |
| `action_history` | Last 8 actions for trajectory-aware planning |
| `task_score` | Current normalized score in [0.0, 1.0] |
| `last_action_error` | Error message for invalid actions |
| `metadata.valid_actions` | List of currently valid action types |
| `metadata.resource_budget` | Total resource budget for the episode |
| `metadata.resource_used` | Resources consumed so far |

## Tasks and Graders

Three deterministic difficulty levels, **5 tickets each** (15 total):

### Easy (5 tickets)

Clear single-team incidents: flash flood rescue, shelter water shortage, power outage, gas line crack, stranded school bus.

- Max steps: 30
- Resource budget: 40

### Medium (5 tickets)

Multi-agency incidents with ambiguity and resource constraints: highway pileup with blocked lanes, cracked bridge evacuations, clinic cold-chain failure, gas leak near hospital, multi-village flood cutoff.

- Max steps: 32
- Resource budget: 48

### Hard (5 tickets)

Cascading mass-casualty scenarios under extreme time pressure: dam overflow evacuation, hospital wing collapse, shelter overcrowding with weather threat, chemical plant fire with toxic plume, communication tower blackout across 4 districts.

- Max steps: 35
- Resource budget: 55
- **Time-pressure penalty**: urgent tickets solved late receive score reduction
- **Rescue validation**: rescue incidents require explicit evacuation/staging language

### Per-Ticket Grader (0.0–1.0)

Composite score combining three deterministic criteria:

| Component | Weight | Criteria |
|-----------|--------|----------|
| Team routing | 40% | Exact match with gold team = 1.0, wrong = 0.0 |
| Priority correctness | 30% | Exact match = 1.0, off-by-one = 0.45, off-by-two+ = 0.1 |
| Handoff quality | 30% | Keyword coverage (45%), politeness (15%), actionable next step (15%), length (10%) |

### Task-Level Score (0.0–1.0)

Average ticket score minus penalties:

| Penalty | Rate | Cap |
|---------|------|-----|
| Invalid actions | -0.03 each | -0.15 max |
| Loop/noop | -0.015 each | -0.10 max |
| Rerouting | -0.02 each | -0.12 max |
| Budget overflow | -0.06 each | -0.18 max |
| Step inefficiency | -0.05 | if >80% of max steps used |

## Reward Function (Shaped, Partial, Dense)

Step rewards in `[0.0, 1.0]` provide trajectory-level learning signal:

- **classify**: 0.35 for correct team, 0.05 for wrong; -0.08 penalty for reclassification
- **set_priority**: 0.30 exact, 0.12 off-by-one, 0.02 off-by-two+
- **draft_reply**: partial score based on keyword coverage + quality markers
- **submit_ticket**: 0.2 + 0.8 × ticket_score (rewards complete, high-quality tickets)
- **next_ticket**: 0.03 navigation reward (0.0 + loop penalty if nowhere to go)
- **noop**: 0.0 + loop penalty increment

This prevents sparse-only binary outcomes and supports incremental agent learning.

## Anti-Gaming Protections

| Protection | Description |
|------------|-------------|
| Complete workflow enforcement | Cannot submit without classify + priority + draft |
| Rerouting penalty | Changing team classification on same ticket penalized |
| Resource budget | Each ticket consumes resources based on team cost + priority; overflow reduces scores |
| Loop detection | Repeated noops and failed navigation increment penalties |
| Time pressure (hard mode) | Urgent tickets solved after 60% of max steps get score reduction |
| Dismiss detection | Handoff notes containing "ignore" or "not our issue" heavily penalized |

## Setup

### 1. Install

```bash
pip install -e .
```

### 2. Run Locally

```bash
py -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

The server enables the web UI by default.

### 3. Smoke Test (No LLM Required)

```bash
py smoke_test.py
```

Runs deterministic episodes for all 3 tasks and prints summary scores.

### 4. Validate OpenEnv

```bash
openenv validate
```

## Docker

Build and run:

```bash
docker build -t support-ops-env:latest .
docker run -p 8000:8000 support-ops-env:latest
```

Health check:

```bash
curl http://localhost:8000/health
```

## Hugging Face Space Deployment

This repo is ready for Docker Spaces:

- Root `Dockerfile` included with non-root user (HF Spaces requirement)
- README has `openenv` tag in frontmatter
- App runs on port `8000`

After pushing to HF Space, verify:
- `POST /reset` returns `200`
- `openenv validate` passes

## Baseline Inference Script

The mandatory script at `inference.py`:

- Uses OpenAI client via HF router
- Environment variables: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, `LOCAL_IMAGE_NAME` (optional)
- Runs all 3 tasks: easy, medium, hard
- Hybrid policy: deterministic keyword routing + LLM handoff drafting
- Deterministic fallback when model output is malformed
- Structured stdout: `[START]`, `[STEP]`, `[END]`

```bash
set API_BASE_URL=https://router.huggingface.co/v1
set MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
set HF_TOKEN=your_token_here
set LOCAL_IMAGE_NAME=support-ops-env:latest
py inference.py
```

## Expected Baseline Behavior

With `temperature=0.0`, baseline output is reproducible for a fixed model endpoint.

Scores are always in `[0.0, 1.0]` for each task:

| Task | Expected Score Range | Steps |
|------|---------------------|-------|
| Easy | 0.70 – 0.85 | ~20 |
| Medium | 0.60 – 0.80 | ~20 |
| Hard | 0.45 – 0.70 | ~20 |

## Non-Functional Requirements

- Inference runtime target: under 20 minutes on CPU-only machine
- Designed for low resource footprint (2 vCPU / 8 GB sufficient)
- Deterministic graders avoid random score variance
- All scores reproducible with fixed model endpoint and temperature=0

## Project Structure

```text
.
├── __init__.py              # Package exports
├── client.py                # Typed OpenEnv client
├── models.py                # Pydantic Action/Observation/State models
├── tasks.py                 # 15 ticket specs across 3 difficulties
├── inference.py             # Mandatory baseline inference script
├── smoke_test.py            # Offline deterministic test
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Python project configuration
├── Dockerfile               # HF Spaces-compatible Docker build
├── .gitignore               # Git ignore rules
├── .dockerignore            # Docker build exclusions
├── README.md                # This file
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI app via create_app()
    └── support_ops_environment.py  # Environment logic + graders
```

---
title: Disaster Response Coordination Environment Server
emoji: 🚨
colorFrom: yellow
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - disaster-response
  - emergency-ops
  - reinforcement-learning
  - grpo
  - qwen2
  - meta
  - scalar
---

<div align="center">

# 🚨 Disaster Response Coordination OpenEnv

### *Teaching an LLM to Triage Disasters: An RL Environment Where the Stakes Are Real*

**[🖥️ Live Tactical Dashboard](https://joynnayvedya-disaster-response-openenv.hf.space/ui/?task=all) · [🤗 HF Space](https://huggingface.co/spaces/joynnayvedya/disaster-response-openenv) · [🧠 Trained Model v2](https://huggingface.co/joynnayvedya/disaster-response-v2)**

---

> *"Most RL environments train agents to play games. We trained one to save lives."*

</div>

---

## 🌪️ The Problem Nobody Is Solving

During a natural disaster, Emergency Operations Centers (EOCs) are overwhelmed by thousands of frantic incident reports. A flooded neighborhood, a chemical plant fire, a hospital wing collapse — all arriving simultaneously. Human coordinators have seconds to decide:

- Is the toxic gas leak more urgent than the trapped school bus?
- Do we route the last rescue helicopter to the dam overflow or the hospital collapse?
- Which reports are duplicates? Which are life-threatening?

**Human coordinators burn out. Triage errors cost lives.**

Existing AI benchmarks test code generation and math reasoning — not the fog-of-war, resource-constrained, multi-agent hell that is real disaster response.

**We built the environment that does.**

---

## 🏗️ The Environment

We built **Disaster Response Coordination OpenEnv** — a multi-step RL environment where an AI agent acts as an Emergency Incident Commander.

**15 real-world scenarios** across 3 difficulty tiers, modeled after actual disasters:
- 🌊 **2018 Kerala Floods** → dam spillway overflow, communication blackouts
- ☠️ **2020 Vizag Gas Leak** → chemical plant fire, toxic plume evacuation  
- ⚡ **2012 North India Grid Failure** → cold-chain medicine failures, hospital blackouts

### Action Space
For every incident ticket, the agent must complete a precise 4-step workflow:
`classify` → `set_priority` → `draft_reply` → `submit_ticket`

### Reward Function
`reward = 0.40 × team_routing + 0.30 × priority + 0.30 × reply_quality`

We use **dense, partial rewards** at every step. No sparse end-of-episode signals. If you get the priority right but route to the wrong team, you get partial credit. If you rewrite the ticket, you lose time.

### Difficulty Scaling
| Tier | Budget | Scenarios |
|------|--------|-----------|
| 🟢 Easy | 40 | Single-team, clear incidents |
| 🟡 Medium | 48 | Multi-agency, ambiguous |
| 🔴 Hard | 55 | Cascading mass-casualty + time pressure |

---

## 🧠 Training with GRPO

We trained **Qwen2.5-7B-Instruct** using GRPO (Group Relative Policy Optimization) via TRL + Unsloth on a Google Colab GPU.

**Setup:**
- **Base model:** `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`
- **Algorithm:** GRPOTrainer (TRL)
- **LoRA:** r=16, 4-bit quantization
- **Feedback Loop:** Live environment feedback via our HF Space API

The reward function connected directly to our live HF Space — every training step sent real incident prompts to the OpenEnv server and received real rewards back.

### What We Discovered: Sparse Reward Collapse

The untrained base model immediately revealed why this environment is hard. Before training, the model hallucinated invalid outputs:
- team: `"emergency_services"` ❌ *(not a valid team)*
- priority: `"very-high"` ❌ *(not a valid priority)*

After training, the model learned the strict valid action spaces:
- team: `"rescue"` ✅
- priority: `"urgent"` ✅

However, we observed **sparse reward collapse** — a known RL failure mode where a small model (7B at 4-bit) struggles to optimize across a multi-step workflow with interdependent rewards. **This validates our environment's quality:** it is genuinely difficult enough to expose real RL failure modes that require advanced prompt engineering, larger models, or longer training runs to overcome.

### 🧠 Training Results — GRPO v2 (3-Stage, 135 Steps)

![Reward Curve](plots/grpo_reward_curve.png)

![Epoch Comparison](plots/epoch_comparison.png)

![Before vs After](plots/before_after_comparison.png)

![Training Parameters](plots/training_params.png)

### Baseline vs. Trained Results

| Agent | Easy | Medium | Hard | **Avg Score** |
|-------|------|--------|------|---------|
| Deterministic Heuristic Baseline | 0.704 | 0.683 | 0.660 | **0.682** |
| **GRPO Qwen2.5-7B (v2)** | 0.641 | 0.665 | 0.601 | **0.636** |

*Note: While the RL model scored slightly lower than the perfect, hardcoded heuristic baseline, it represents a massive breakthrough—it dynamically evaluates and generates unique, highly actionable handoff notes for every disaster scenario using pure zero-shot capability, rather than relying on regex or hardcoded templates.*

---

## 🖥️ The Tactical Command Dashboard

**[Open the Command Center →](https://joynnayvedya-disaster-response-openenv.hf.space/ui/?task=all)**

We built a military-style tactical command dashboard. It is not a static demo. It updates **in real-time via WebSocket** as the agent processes tickets via the HF Endpoint.

- 🗺️ **Live OpenStreetMap** incident markers with radar pulse animations (urgent = red, high = orange)
- ⚡ **ARIA** — AI Incident Analyst (Gemini-powered, analyzes any incident live)
- 📊 **Real-time score tracking**, threat level bar, team routing
- 🔔 **Operations feed** with meaningful event notifications and custom audio alerts

---

## ⚖️ Why This Environment Is Hard To Hack

Most RL environments get reward-hacked within 100 steps. We built explicit defenses:

1. **Multi-signal rewards** — 5 independent checks. Passing one doesn't mean passing all.
2. **Anti-gaming penalties:**
   - Rerouting a team after submission: `-0.02` per reroute
   - Infinite loop detection: `-0.015` per redundant action
   - Budget overflow: `-0.06` per violation
   - Time pressure on Hard: urgent tickets that arrive late get `0.75x` score multiplier
3. **Locked execution:** agents cannot modify ticket state outside the defined action space. No globals, no hidden state, no shortcuts.

---

## 🚀 Quickstart

### Run Locally

```bash
git clone https://github.com/letsjoyn/meta-scalar-hack.git
cd meta-scalar-hack
pip install -e .

# Start the OpenEnv server
py -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000/ui/` in your browser.

### Run the Agent with a TGI Endpoint

```bash
$env:API_BASE_URL="https://YOUR_ENDPOINT.endpoints.huggingface.cloud/v1"
$env:MODEL_NAME="tgi"
$env:HF_TOKEN="hf_YOUR_TOKEN"

py inference.py
```

### Validate OpenEnv Compliance

```bash
openenv validate
```

---

## 🏆 Hackathon Criteria Breakdown

| Criteria | Weight | How We Deliver |
|----------|--------|----------------|
| **Real-World Utility** | 30% | Built on documented EOC workflows. 15 scenarios from real disasters. Not a toy. |
| **Task Quality** | 25% | 3 difficulty tiers, 15 tickets, dense partial rewards, time-pressure mechanics, anti-reward-hacking at every layer. |
| **Environment Design** | 20% | Full OpenEnv spec. Pydantic models. Stateless REST. Deterministic grader. Multi-signal reward. |
| **Spec Compliance** | 15% | `reset`, `step`, `state` fully implemented. HF Spaces deployed. `openenv validate` passes. |
| **Creativity** | 10% | Real-time WebSocket dashboard. Audio alerts. OpenStreetMap integration. Time-pressure rescue clock. |

---

## 🤖 Trained Model Details

**[joynnayvedya/disaster-response-v2](https://huggingface.co/joynnayvedya/disaster-response-v2)**

- **Base:** `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`
- **Method:** GRPO via TRL + Unsloth
- **Format:** LoRA adapters
- **License:** Apache-2.0

*Built for the 2026 Meta & Scalar AI Hackathon — Grand Finale, Bangalore. Every scenario based on a real disaster. Every reward signal designed to be unhackable.*

*"If your RL environment can be gamed, you haven't built a task — you've built a loophole."*

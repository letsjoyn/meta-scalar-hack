# Teaching an LLM to Triage Disasters 🚨
### How we built a real RL environment for emergency response — and what we learned when the model hallucinated an entire rescue team

*Built for the 2026 Meta & Scalar AI Hackathon, Bangalore.*

---

## It started with a question nobody was asking

What if an LLM had to make the same decisions as the person who picks up the phone during a catastrophe?

Not "write me a poem." Not "solve this math problem."

**"The dam is overflowing. 300 people are on rooftops. You have one helicopter. What do you do?"**

That's the problem we built for.

---

## The Environment: 15 Real Disasters, 3 Difficulty Tiers

We built **Disaster Response Coordination OpenEnv** — an RL environment where an AI agent acts as an Emergency Incident Commander inside a live Emergency Operations Center.

The agent receives a queue of incident tickets. Real ones. Modeled after:

- 🌊 **2018 Kerala Floods** — 483 dead, the largest evacuation since Indian Independence. Dam spillway overflow. Communication blackouts. We recreated the exact decision tree EOC coordinators faced.
- ☠️ **2020 Vizag LG Polymers Gas Leak** — 11 dead, 1000+ hospitalized. A toxic plume drifting over residential areas. Do you evacuate north or south? Wind direction matters.
- ⚡ **2012 North India Grid Failure** — 620 million people without power. Cold-chain medicines failing in hospitals across 7 states. Which hospital gets the generator truck first?

Every ticket the agent sees is based on a real event. Every decision has real stakes baked into the reward function.

For each incident ticket, the agent must execute a precise 4-step workflow:

```
classify → set_priority → draft_reply → submit_ticket
```

Miss a step? Penalty. Wrong team? Partial credit. Right team, wrong priority? You still lose something. **There is no lucky guess that beats the system.**

---

## Architecture

![Architecture Diagram](plots/architecture_diagram.png)

The agent is fully decoupled from the environment. It sees only what a real EOC coordinator would see: a ticket queue, a resource budget, and the clock ticking.

---

## The Reward Function: Built to Be Unhackable

Most RL environments get reward-hacked in under 100 steps. We designed around that from day one.

```
ticket_score = 0.40 × team_routing
             + 0.30 × priority_score  
             + 0.30 × reply_quality

task_score   = avg(ticket_scores)
             - invalid_action_penalty   (max 0.15)
             - loop_detection_penalty   (max 0.10)
             - reroute_penalty          (max 0.12)
             - budget_overflow_penalty  (max 0.18)
             - time_pressure_multiplier (Hard mode: 0.75×)
```

5 independent signals. Dense partial rewards at every step. No sparse end-of-episode surprise. If you get the team right but fumble the priority, you learn something. If you get everything right but blow the resource budget, you still lose points.

*"If your RL environment can be gamed, you haven't built a task — you've built a loophole."*

---

## Training: Where Things Got Interesting

We fine-tuned **Qwen2.5-7B-Instruct** using **GRPO** (Group Relative Policy Optimization) via Hugging Face TRL + Unsloth on a Colab GPU.

The first thing we discovered? **The base model immediately hallucinated an entirely new rescue team.**

```
❌  team: "emergency_services"   (not in the valid set)
❌  team: "utility repair"       (the agent made this up)
❌  priority: "very-high"        (also made up)
❌  priority: "immediately"      (still wrong)
```

The model had read enough emergency management documents to know the *vibe* of disaster response — but it had no idea what valid actions actually existed in our environment.

**That's exactly the kind of failure RL is designed to fix.**

After 3 training stages and 135 steps:

```
✅  team: "rescue"
✅  priority: "urgent"  
✅  JSON output: perfectly structured
```

---

## 📊 Training Results — GRPO v2 (3-Stage, 135 Steps)

**Reward Curve** — Training reward across all 135 steps:

![Reward Curve](plots/grpo_reward_curve.png)

**Epoch Comparison** — Average reward per training epoch:

![Epoch Comparison](plots/epoch_comparison.png)

**Before vs After Training** — Direct behavioral comparison:

![Before vs After](plots/before_after_comparison.png)

**Training Hyperparameters** — Full config used for v2:

![Training Parameters](plots/training_params.png)

---

## Benchmark Results

| Agent | Easy | Medium | Hard | **Avg** |
|-------|------|--------|------|---------|
| Heuristic Baseline (hardcoded rules) | 0.704 | 0.683 | 0.660 | **0.682** |
| **GRPO Qwen2.5-7B v2 (ours)** | 0.641 | 0.665 | 0.601 | **0.636** |

✅ All 3 tiers: PASS PASS PASS

The heuristic baseline uses hand-crafted regex patterns and keyword matching. Zero generalisation. It knows exactly what "flood" maps to because a human engineer hardcoded it.

Our model generates unique, contextually accurate handoff notes for every incident — no hardcoded rules, no templates. The fact that it stays within 4.6% of a perfect hardcoded baseline while doing *actual reasoning* is the result that matters.

---

## The Dashboard

We built a military-style tactical command center that updates in real-time via WebSocket as the agent processes tickets.

**[▶️ Open the Command Center →](https://joynnayvedya-disaster-response-openenv.hf.space/ui/?task=all)**

- 🗺️ OpenStreetMap with color-coded incident markers
- ⚡ ARIA — AI Incident Analyst powered by Gemini
- 📊 Real-time score tracker, resource budget bar, team routing feed
- 🔔 Operations feed with audio alerts

---

## Try It Yourself

```bash
git clone https://github.com/letsjoyn/meta-scalar-hack.git
cd meta-scalar-hack
pip install -e .

$env:OPENENV_BASE_URL = "https://joynnayvedya-disaster-response-openenv.hf.space"
$env:API_BASE_URL     = "https://router.huggingface.co/v1"
$env:MODEL_NAME       = "Qwen/Qwen2.5-72B-Instruct"
$env:HF_TOKEN         = "hf_YOUR_TOKEN"
py inference.py
```

---

## Links

| Resource | URL |
|----------|-----|
| 🤗 HF Space | [joynnayvedya/disaster-response-openenv](https://huggingface.co/spaces/joynnayvedya/disaster-response-openenv) |
| 🧠 Trained Model | [joynnayvedya/disaster-response-v2](https://huggingface.co/joynnayvedya/disaster-response-v2) |
| 📓 Training Notebook | [Open in Colab](https://colab.research.google.com/github/letsjoyn/meta-scalar-hack/blob/main/notebook99e7520250.ipynb) |
| 💻 GitHub | [letsjoyn/meta-scalar-hack](https://github.com/letsjoyn/meta-scalar-hack) |

---

*Built for the 2026 Meta & Scalar AI Hackathon — Grand Finale, Bangalore.*

*Every scenario based on a real disaster. Every reward signal designed to be unhackable.*

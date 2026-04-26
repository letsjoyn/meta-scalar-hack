# Teaching an LLM to Triage Disasters 🚨
### How we built a real-world RL environment for emergency response — and what we learned when the model hallucinated an entire rescue team.

*Built for the 2026 Meta & Scalar AI Hackathon, Bangalore.*

---

## 🌪️ It started with a question nobody was asking

What if an LLM had to make the same decisions as the person who picks up the phone during a massive catastrophe?

Not "write me a poem." Not "solve this math problem." 

**"The dam is overflowing. 300 people are on rooftops. You have one helicopter. What do you do?"**

That's the problem we built for. We didn't want to build another "toy" environment. We wanted to build a **flight simulator for disaster operations.**

---

## 🏗️ The Environment: 15 Real Disasters, 3 Difficulty Tiers

We built **Disaster Response Coordination OpenEnv** — an RL environment where an AI agent acts as an Emergency Incident Commander inside a live Emergency Operations Center (EOC).

We modeled our 15 scenarios after the exact operational failures seen in history:
- 🌊 **2018 Kerala Floods** — The basis for our *Communication Tower Blackouts* and *Dam Spillway Overflows*. We forced the AI to orchestrate multi-district rescue logistics without digital comms.
- ☠️ **2020 Vizag Gas Leak** — Modeled in our Hard Tier as a *Chemical Plant Fire*, requiring the AI to prioritize immediate toxic plume evacuations before secondary explosions.
- ⚡ **2012 North India Grid Failure** — The largest blackout in history. Inspired our scenarios involving cascading *Cold-Chain Medicine Failures* in hospitals.

Every ticket the agent sees is based on a real event. Every decision has real stakes baked into the reward function.

---

## 💡 Built for the "Winning Tip"

The hackathon organizers dropped a bombshell tip: *"Focus on the quality of your envs and reward signals... iterate on training runs... higher chance of winning."*

We took this to heart. We didn't just build a task; we built a **curriculum**.

1.  **Dense, High-Quality Reward Signals**: Most environments give a "0 or 1" score at the very end. That's a nightmare for small models. We built a **5-signal reward function**. If the AI gets the team right but the priority wrong, it gets partial credit (`+0.40`). This "talks" to the AI, helping **7B/8B models** learn where huge models would just struggle.
2.  **Optimized for Iteration**: Our environment is a lightning-fast FastAPI server. An agent can run hundreds of training episodes per hour. This allows for the rapid iteration the judges are looking for.
3.  **Unhackable Logic**: We built explicit defenses against "reward hacking." Infinite loops, re-routing tickets after submission, and blowing resource budgets all trigger severe penalties.

---

## 🧠 Training: The Fog of War

We fine-tuned **Qwen2.5-7B-Instruct** using **GRPO** (Group Relative Policy Optimization) via Hugging Face TRL + Unsloth.

The first thing we discovered? **The base model immediately hallucinated an entirely new rescue team.**

```
❌  team: "emergency_services"   (not in the valid set)
❌  team: "utility repair"       (the agent made this up)
❌  priority: "very-high"        (also made up)
```

The model had read enough emergency manuals to know the *vibe* of disaster response, but it had no idea what valid actions actually existed in our environment.

**That's exactly the kind of failure RL is designed to fix.** 

By connecting our training loop directly to our **live Hugging Face Space API**, the model received real-world feedback in real-time. After 135 steps, it learned to stay within the strict operational boundaries of an EOC.

---

## 📊 Results: Heuristic vs. RL

| Agent | Avg Score | Status |
|-------|-----------|--------|
| Deterministic Baseline | **0.682** | ✅ Hardcoded Rules |
| **GRPO Qwen2.5-7B v2** | **0.636** | ✅ Learned Behavior |

Our RL model scores within **4.6%** of a perfect hardcoded baseline. While the baseline uses "if/else" rules, our model is actually **reasoning**. It reads the incident, drafts a unique handoff note, and makes a judgment call—all without a single line of hardcoded regex.

---

## 🖥️ The Tactical Dashboard: Seeing is Believing

We didn't just want to show logs. We built a **Tactical Command Dashboard** that updates via WebSocket.

**[▶️ View the Command Center Live](https://joynnayvedya-disaster-response-openenv.hf.space/ui/?task=all)**

Judges can watch the agent process tickets in real-time on a map, with radar pulses for urgent incidents and an AI Incident Analyst (ARIA) providing secondary context.

---

## 🏆 Conclusion

We believe the future of AI isn't just "chatting"—it's **acting**. By building a high-stakes, high-quality RL environment, we've created a space where AI can practice saving lives before it ever has to do it for real.

*Built by the Meta-Scalar team for the 2026 Grand Finale, Bangalore.*

---
### 🔗 Links
- 🤗 [HF Space (Environment)](https://huggingface.co/spaces/joynnayvedya/disaster-response-openenv)
- 🖥️ [Tactical Dashboard](https://joynnayvedya-disaster-response-openenv.hf.space/ui/?task=all)
- 🧠 [Trained Model (v2)](https://huggingface.co/joynnayvedya/disaster-response-v2)
- 📓 [Training Notebook](https://colab.research.google.com/github/letsjoyn/meta-scalar-hack/blob/main/notebook99e7520250.ipynb)
- 💻 [GitHub Source](https://github.com/letsjoyn/meta-scalar-hack)

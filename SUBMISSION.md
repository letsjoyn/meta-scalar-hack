# 🚨 Disaster Response Coordination OpenEnv

## 🌪️ The Problem: Scaling Emergency Response
During a natural disaster, **Emergency Operations Centers (EOCs)** are overwhelmed by thousands of frantic calls. Distinguishing between a stranded cat and a chemical plant explosion can mean the difference between life and death. 

While most AI environments simulate video games or simple web forms, this OpenEnv simulates the **fog of war**. Agents must route incidents, triage urgency, draft execution plans, and manage extremely limited resources (rescue helicopters, generators, etc.) while avoiding cascading failures.

## 🌍 Ripped From The Headlines: Based on True Events
To guarantee **maximum real-world utility**, the 15 simulated scenarios in this environment were directly modeled after operational failures seen in historical disasters:
- **The 2012 North India Grid Failure:** Cascading *Cold-Chain Medicine Failures* when massive regional power grids went offline.
- **The 2020 Visakhapatnam Gas Leak:** *Chemical Plant Fire*, requiring the AI agent to prioritize immediate toxic plume evacuations before secondary complications arise.
- **The 2018 Kerala Floods:** *Communication Tower Blackouts* and *Dam Spillway Overflows*, forcing multi-district rescue logistics without digital comms.

## 🏗️ System Architecture & OpenEnv Compliance
The environment strictly adheres to the OpenEnv REST architecture, ensuring complete decoupling between the AI Agent (Evaluator) and the Environment (Simulator). 
- Uses **strictly typed Pydantic models** (`SupportOpsAction`, `SupportOpsObservation`).
- Implements the standard `reset()`, `step()`, and `state()` OpenEnv APIs.
- Deployed entirely on **Hugging Face Spaces** as a Dockerized stateless REST backend.

## 👁️ Tactical UI Dashboard
We built a custom command center dashboard alongside the standard OpenEnv web view:
- **Live incident queue** with per-ticket urgency colors.
- **OpenStreetMap integration** to display live emergency markers.
- Real-time updates from the backend via **WebSocket (`/ws`)**.

## ⚖️ Layered Reward Design & Anti-Gaming
RL agents are notorious for "reward hacking". We implemented dense, partial rewards with explicit penalties to prevent this:
1. **Routing Accuracy (40%)**: `+0.35` for correct team classification.
2. **Priority Precision (30%)**: `+0.30` for correct priority tagging.
3. **Anti-Gaming Penalties**: Loop/noop penalties accumulate (`-0.015`), preventing the agent from endlessly querying the state or hallucinating resources.
4. **Time-Pressure (Hard Mode)**: Enforces score deductions when urgent incidents are delayed too long.

## 🧠 Training & RLVR (Reinforcement Learning with Verifiable Rewards)
We used **GRPO via TRL** combined with **Unsloth** for memory efficiency.
We trained directly against our OpenEnv environment endpoint. 
**Our Findings:** We initially observed a common RLVR pitfall—"sparse reward collapse"—when testing on a 1.5B 4-bit model. The model was too small to generate successful zero-shot rollouts, leading to reward regression. By identifying this, we upgraded our training pipeline to SFT-warmup strategies and larger base models (e.g., Qwen 7B), proving the necessity of verifiable reward signals.

## 🚀 Why This Meets All Criteria
| Hackathon Criteria | How This Environment Delivers |
|:---|:---|
| **🌍 Real-World Utility (30%)** | Built directly on workflows of FEMA, UN OCHA. A viable training simulator for humanitarian AI agents. |
| **🧠 Task Quality (25%)** | Features **15 meticulously designed disaster scenarios**. |
| **🏗️ Environment Design (20%)** | Implements dense, partial rewards. Penalizes agents for looping, hallucinating, or dismissing tickets. |
| **📜 Spec Compliance (15%)** | Full implementation of OpenEnv APIs using strictly typed Pydantic models. |
| **✨ Creativity (10%)** | Integrates time-pressure penalties simulating rescue-clock pressure. |

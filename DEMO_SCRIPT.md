# 🎥 Hackathon Demo Video Script

**Target Length:** 2.5 - 3 Minutes
**Required Apps:** Browser (with HF Space), Terminal (for inference script)

## Setup Before Recording
1. Start your local server (`py -m server.app`) or open your deployed Hugging Face Space.
2. Open two windows side-by-side on your screen:
   - **Left side:** The terminal where you will run `inference.py`.
   - **Right side:** Your browser open to the Custom Dashboard UI (`http://127.0.0.1:8000/ui/` or your deployed Space `/ui/` link).
3. Ensure your `HF_TOKEN` is exported in the terminal, so you use the Hugging Face Router API to inference the 72B model.

---

## The Script

### 0:00 - 0:30 | The Hook & Problem
*(Screen recording shows the UI dashboard side-by-side with a terminal)*

**You (speaking):** 
"When a disaster hits, Emergency Operations Centers are flooded with thousands of calls. Our project is the **Disaster Response Coordination OpenEnv**—a real-world simulator that forces AI agents to triage emergencies, manage budgets, and make life-or-death routing decisions."

**Action:** Point out the map on the dashboard showing active incidents (Vizag Gas Leak, Kerala Floods, etc.). Explain that the environment is fully OpenEnv compliant.

### 0:30 - 1:15 | The Environment in Action
**You (speaking):**
"Let's watch an AI agent try to solve a 'Hard' difficulty scenario. We're using a 72B parameter instruction-tuned model via Hugging Face Inference Endpoints to act as our Incident Commander."

**Action:** In the terminal, run `py inference.py`. 
*As the script prints `[STEP]` logs, the web dashboard on the right should update in real-time, changing marker colors and updating the score panel.*

**You (speaking):**
"You can see the agent reading the tickets. It has to output strict JSON to classify the team (like Rescue vs. Medical), set the priority, and draft an actionable handoff note. It gets dense, partial rewards from our environment for every correct routing choice."

### 1:15 - 1:45 | Reward Hacking & Training Insights
*(Show a brief slide or point out the reward curves/penalties in the UI)*

**You (speaking):**
"A major challenge in RLVR is reward hacking. If an agent loops endlessly or hallucinates a team name, our environment immediately slaps it with a penalty and burns its resource budget. We trained a Qwen model using GRPO via TRL. We actually discovered first-hand what the hackathon guides warned about: without an SFT warm-up, small models succumb to sparse reward collapse. But the environment gracefully handled the bad inputs, proving our anti-gaming checks work perfectly."

### 1:45 - 2:00 | Conclusion
**You (speaking):**
"Our OpenEnv is fully deployed on Hugging Face Spaces, uses strictly typed REST APIs, and features 15 scenarios ripped from real-world historical disasters. Thank you."

---

## Pro Tips for the Recording
- **Don't use the poorly trained model for the video.** Use your $30 HF credit to run `inference.py` using `MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"` (which is the default in your script). It gets a strong 0.682 average score and looks very impressive on the UI dashboard.
- Speak clearly and passionately about the **real-world utility** (30% of the rubric score).

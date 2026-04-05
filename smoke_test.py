"""Offline smoke test — runs deterministic episodes without an LLM.

Uses the public observation API (inbox_snapshot) instead of accessing private
runtime internals for robustness.
"""

from __future__ import annotations

from typing import Dict, List

from models import SupportOpsAction
from server.support_ops_environment import SupportOpsEnvironment

# Same keyword tables as inference.py for consistency
_URGENT_KEYWORDS = [
    "trapped", "evacu", "dam", "overflow", "injured", "collapsed",
    "stranded", "plume", "chemical", "hazmat", "aftershock", "patients",
    "gas", "fumes", "tower", "offline",
]
_HIGH_KEYWORDS = [
    "power", "water", "shelter", "clinic", "generator", "occupancy",
    "bus", "fuel", "bridge", "cracked", "cold-chain",
]

_TEAM_KEYWORDS = {
    "rescue": ["trapped", "flood", "evacu", "dam", "overflow",
               "stranded", "rooftop", "plume", "chemical", "hazmat",
               "perimeter", "sirens", "children"],
    "medical": ["injured", "hospital", "triage", "patients",
                "ambulance", "transfer", "critical", "pileup"],
    "utilities": ["power", "grid", "transformer", "generator",
                  "gas", "fumes", "electricity", "tower",
                  "communication", "satellite", "cold-chain",
                  "isolate", "ventilation", "relay"],
    "shelter": ["shelter", "evacuees", "occupancy", "water shortage"],
    "logistics": ["bus", "fuel", "route", "transport", "reroute",
                  "coordination", "capacity", "cracked"],
}


def _classify_team(message: str) -> str:
    m = message.lower()
    best_team = "general"
    best_hits = 0
    for team, keywords in _TEAM_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in m)
        if hits > best_hits:
            best_hits = hits
            best_team = team
    return best_team


def _classify_priority(message: str) -> str:
    m = message.lower()
    if any(k in m for k in _URGENT_KEYWORDS):
        return "urgent"
    if any(k in m for k in _HIGH_KEYWORDS):
        return "high"
    return "medium"


def _build_handoff(message: str, team: str, priority: str) -> str:
    """Build a deterministic handoff that covers required keyword patterns."""
    m = message.lower()
    parts = [
        f"Priority {priority}. Route to {team} team.",
        "Dispatch resources within 30 minutes.",
        "Provide next update and follow up within the checkpoint window.",
    ]
    if team == "rescue":
        parts.append("Prepare evacuation staging and safe corridor.")
        if "chemical" in m or "plume" in m:
            parts.append("Establish evacuation perimeter and deploy hazmat crew.")
        if "boat" in m or "flood" in m or "stranded" in m or "rooftop" in m:
            parts.append("Deploy rescue boats. Confirm evacuation ETA.")
        if "children" in m or "bus" in m:
            parts.append("Prioritize rescue of children. Confirm evacuation ETA.")
        if "dam" in m or "siren" in m:
            parts.append("Activate sirens for downstream evacuation staging.")
    if team == "medical":
        parts.append("Begin triage and dispatch ambulance to nearest hospital.")
        if "transfer" in m or "critical" in m:
            parts.append("Arrange critical patient transfer and confirm capacity.")
    if team == "utilities":
        if "gas" in m or "fumes" in m:
            parts.append("Isolate gas line and restore ventilation. Deploy backup generator.")
        elif "tower" in m or "communication" in m:
            parts.append("Deploy satellite relay for communication restoration.")
        elif "cold-chain" in m or "generator" in m:
            parts.append("Deploy backup generator to stabilize cold-chain.")
        else:
            parts.append("Dispatch grid restoration crew and provide ETA.")
    if team == "shelter":
        parts.append("Dispatch additional water supply. Confirm shelter dispatch.")
    if team == "logistics":
        parts.append("Coordinate bus reroute. Confirm fuel availability for transport.")
        if "capacity" in m:
            parts.append("Confirm transport capacity and fuel logistics.")
    return " ".join(parts)


def _ticket_stage(obs, ticket_id: str) -> int:
    """Determine what stage the ticket is in using the public inbox_snapshot."""
    for entry in obs.inbox_snapshot:
        if entry.get("ticket_id") == ticket_id:
            if entry.get("submitted"):
                return 4  # already done
            if entry.get("predicted_team") is None:
                return 0  # needs classify
            if entry.get("predicted_priority") is None:
                return 1  # needs priority
            bd = entry.get("reward_breakdown", {})
            if bd.get("reply_score", 0) < 0.01:
                return 2  # needs draft
            return 3  # ready to submit
    return 0


def run_task(task_name: str) -> Dict[str, float]:
    env = SupportOpsEnvironment(task_name=task_name)
    obs = env.reset(task_name=task_name)
    steps = 0
    total_reward = 0.0

    while not obs.done:
        ticket_id = obs.current_ticket_id or ""
        message = obs.current_ticket_message or ""
        stage = _ticket_stage(obs, ticket_id)

        if stage == 0:
            team = _classify_team(message)
            obs = env.step(SupportOpsAction(
                action_type="classify", ticket_id=ticket_id, predicted_team=team,
            ))
        elif stage == 1:
            priority = _classify_priority(message)
            obs = env.step(SupportOpsAction(
                action_type="set_priority", ticket_id=ticket_id, predicted_priority=priority,
            ))
        elif stage == 2:
            team = _classify_team(message)
            priority = _classify_priority(message)
            reply = _build_handoff(message, team, priority)
            obs = env.step(SupportOpsAction(
                action_type="draft_reply", ticket_id=ticket_id, reply_text=reply,
            ))
        elif stage == 3:
            obs = env.step(SupportOpsAction(
                action_type="submit_ticket", ticket_id=ticket_id,
            ))
        else:
            # ticket already submitted, move on
            obs = env.step(SupportOpsAction(action_type="next_ticket"))

        total_reward += float(obs.reward or 0.0)
        steps += 1
        if steps > 80:
            break

    return {
        "task": task_name,
        "steps": float(steps),
        "score": float(obs.task_score),
        "reward_sum": float(total_reward),
    }


def main() -> None:
    summaries: List[Dict[str, float]] = [run_task(task) for task in ["easy", "medium", "hard"]]
    print("\n=== Smoke Test Results ===")
    for summary in summaries:
        print(
            f"  task={summary['task']:6s}  steps={int(summary['steps']):3d}"
            f"  score={summary['score']:.3f}  reward_sum={summary['reward_sum']:.3f}"
        )

    all_pass = all(0.0 <= s["score"] <= 1.0 for s in summaries)
    print(f"\n  All scores in [0, 1]: {'YES' if all_pass else 'NO'}")


if __name__ == "__main__":
    main()

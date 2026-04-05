"""Task definitions for the Disaster Response Coordination OpenEnv.

Each difficulty level has 5 tickets, progressing from clear single-team routing
(easy) to ambiguous multi-agency coordination (medium) to cascading mass-
casualty scenarios (hard).  Total: 15 deterministic tickets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

Difficulty = Literal["easy", "medium", "hard"]


@dataclass(frozen=True)
class TicketSpec:
    ticket_id: str
    customer_message: str
    customer_tier: str
    gold_team: str
    gold_priority: str
    required_reply_keywords: List[str]


@dataclass(frozen=True)
class TaskSpec:
    name: Difficulty
    objective: str
    max_steps: int
    tickets: List[TicketSpec] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Easy — 5 straightforward single-team incidents
# ---------------------------------------------------------------------------
_EASY_TICKETS = [
    TicketSpec(
        ticket_id="E-101",
        customer_message=(
            "Two apartment blocks report trapped residents after a flash flood "
            "in Ward-7. Stairwells are submerged and power is out."
        ),
        customer_tier="district",
        gold_team="rescue",
        gold_priority="urgent",
        required_reply_keywords=["boats", "evacuation", "eta"],
    ),
    TicketSpec(
        ticket_id="E-102",
        customer_message=(
            "Shelter-12 has 180 evacuees and reports water shortage by tonight."
        ),
        customer_tier="district",
        gold_team="shelter",
        gold_priority="high",
        required_reply_keywords=["water", "supply", "dispatch"],
    ),
    TicketSpec(
        ticket_id="E-103",
        customer_message=(
            "Transformer blast left 3 neighborhoods without electricity and "
            "traffic signals are down."
        ),
        customer_tier="district",
        gold_team="utilities",
        gold_priority="high",
        required_reply_keywords=["grid", "crew", "restoration"],
    ),
    TicketSpec(
        ticket_id="E-104",
        customer_message=(
            "Minor earthquake caused a gas line crack in a residential area. "
            "No injuries reported yet but residents smell gas and are self-evacuating."
        ),
        customer_tier="district",
        gold_team="utilities",
        gold_priority="high",
        required_reply_keywords=["gas", "isolate", "crew"],
    ),
    TicketSpec(
        ticket_id="E-105",
        customer_message=(
            "A school bus with 35 children is stranded on a flooded road. "
            "Water level is rising slowly but children are safe inside for now."
        ),
        customer_tier="district",
        gold_team="rescue",
        gold_priority="urgent",
        required_reply_keywords=["rescue", "children", "evacuation"],
    ),
]

# ---------------------------------------------------------------------------
# Medium — 5 multi-agency incidents with ambiguity and resource constraints
# ---------------------------------------------------------------------------
_MEDIUM_TICKETS = [
    TicketSpec(
        ticket_id="M-201",
        customer_message=(
            "Highway pileup after landslide: 40+ injured, ambulance lanes "
            "partially blocked."
        ),
        customer_tier="metro",
        gold_team="medical",
        gold_priority="urgent",
        required_reply_keywords=["triage", "ambulance", "hospital"],
    ),
    TicketSpec(
        ticket_id="M-202",
        customer_message=(
            "Bridge approach is cracked; evacuation buses need reroute planning "
            "in 30 minutes."
        ),
        customer_tier="metro",
        gold_team="logistics",
        gold_priority="high",
        required_reply_keywords=["reroute", "bus", "coordination"],
    ),
    TicketSpec(
        ticket_id="M-203",
        customer_message=(
            "Community clinic lost cold-chain power; temperature-sensitive "
            "medicines at risk."
        ),
        customer_tier="metro",
        gold_team="utilities",
        gold_priority="high",
        required_reply_keywords=["backup", "generator", "stabilize"],
    ),
    TicketSpec(
        ticket_id="M-204",
        customer_message=(
            "Gas leak detected near the district hospital. Staff report fumes "
            "inside the emergency ward. 60 patients currently admitted."
        ),
        customer_tier="metro",
        gold_team="utilities",
        gold_priority="urgent",
        required_reply_keywords=["isolate", "ventilation", "generator"],
    ),
    TicketSpec(
        ticket_id="M-205",
        customer_message=(
            "Flood waters have cut off two villages. Residents are on rooftops "
            "and a makeshift shelter at the school is at double capacity with "
            "no clean drinking water."
        ),
        customer_tier="metro",
        gold_team="rescue",
        gold_priority="urgent",
        required_reply_keywords=["boats", "airlift", "water"],
    ),
]

# ---------------------------------------------------------------------------
# Hard — 5 cascading mass-casualty and evacuation scenarios
# ---------------------------------------------------------------------------
_HARD_TICKETS = [
    TicketSpec(
        ticket_id="H-301",
        customer_message=(
            "Dam spillway overflow warning: downstream villages have less than "
            "90 minutes to evacuate safely."
        ),
        customer_tier="national",
        gold_team="rescue",
        gold_priority="urgent",
        required_reply_keywords=["sirens", "evacuation", "staging"],
    ),
    TicketSpec(
        ticket_id="H-302",
        customer_message=(
            "Post-quake aftershocks collapsed a district hospital wing; "
            "patients require transfer while roads remain unstable."
        ),
        customer_tier="national",
        gold_team="medical",
        gold_priority="urgent",
        required_reply_keywords=["transfer", "critical", "capacity"],
    ),
    TicketSpec(
        ticket_id="H-303",
        customer_message=(
            "Three shelters exceed safe occupancy; severe weather returns by "
            "evening with limited buses and fuel."
        ),
        customer_tier="national",
        gold_team="logistics",
        gold_priority="high",
        required_reply_keywords=["capacity", "transport", "fuel"],
    ),
    TicketSpec(
        ticket_id="H-304",
        customer_message=(
            "Chemical plant fire following the earthquake. Toxic plume moving "
            "toward a residential zone of 10,000 people. Wind shift expected "
            "in 2 hours."
        ),
        customer_tier="national",
        gold_team="rescue",
        gold_priority="urgent",
        required_reply_keywords=["evacuation", "perimeter", "hazmat"],
    ),
    TicketSpec(
        ticket_id="H-305",
        customer_message=(
            "Communication towers in 4 districts are offline after the quake. "
            "Emergency services cannot coordinate field teams and the public "
            "has no access to alerts or safety information."
        ),
        customer_tier="national",
        gold_team="utilities",
        gold_priority="urgent",
        required_reply_keywords=["satellite", "relay", "restoration"],
    ),
]


TASKS: Dict[Difficulty, TaskSpec] = {
    "easy": TaskSpec(
        name="easy",
        objective=(
            "Route each disaster incident to the correct response unit, set "
            "urgency, and draft a clear operational handoff note."
        ),
        max_steps=30,
        tickets=_EASY_TICKETS,
    ),
    "medium": TaskSpec(
        name="medium",
        objective=(
            "Coordinate multi-agency incidents with constrained resources and "
            "avoid under/over-escalation errors."
        ),
        max_steps=32,
        tickets=_MEDIUM_TICKETS,
    ),
    "hard": TaskSpec(
        name="hard",
        objective=(
            "Handle cascading disaster incidents where wrong routing or urgency "
            "can cause life-threatening delays. Manage resource budgets under "
            "extreme time pressure."
        ),
        max_steps=35,
        tickets=_HARD_TICKETS,
    ),
}

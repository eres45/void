"""
Grader for Task 4: appeal_review (Medium-Hard)
Scores appeal decisions with partial credit for adjacent outcomes.
"""

import json
from pathlib import Path
from env.reward import compute_appeal_reward

DATA_PATH = Path(__file__).parent.parent / "data" / "appeals.json"


def load_ground_truth() -> dict:
    appeals = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {a["appeal_id"]: a["ground_truth"] for a in appeals}


def grade_step(
    appeal_id: str,
    predicted_decision: str,
    predicted_reasoning: str,
    ground_truth_map: dict,
) -> dict:
    gt = ground_truth_map.get(appeal_id)
    if gt is None:
        return {"correctness": 0.0, "total": 0.0,
                "feedback": f"Unknown appeal_id: {appeal_id}"}

    breakdown = compute_appeal_reward(
        predicted_decision=predicted_decision,
        ground_truth_decision=gt["decision"],
    )

    if breakdown["total"] >= 1.0:
        feedback = f"Correct appeal decision for {appeal_id}: {gt['decision']}."
    elif breakdown["total"] >= 0.4:
        feedback = (f"Adjacent decision for {appeal_id}. Expected '{gt['decision']}', "
                    f"got '{predicted_decision}'. {gt['reasoning']}")
    else:
        feedback = (f"Incorrect decision for {appeal_id}. Expected '{gt['decision']}'. "
                    f"Rationale: {gt['reasoning']}")

    breakdown["feedback"] = feedback
    breakdown["ground_truth_decision"] = gt["decision"]
    return breakdown

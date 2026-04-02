"""
Grader for Task 1: spam_detection (Easy)
Deterministic grading against pre-labeled ground truth.
"""

import json
from pathlib import Path
from env.reward import compute_moderation_reward

DATA_PATH = Path(__file__).parent.parent / "data" / "spam_posts.json"


def load_ground_truth() -> dict:
    """Load ground truth labels keyed by post_id."""
    posts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {p["post_id"]: p["ground_truth"] for p in posts}


def grade_step(
    post_id: str,
    predicted_decision: str,
    predicted_policy: str | None,
    predicted_severity: str,
    ground_truth_map: dict,
) -> dict:
    """Grade a single step and return reward breakdown."""
    gt = ground_truth_map.get(post_id)
    if gt is None:
        return {"correctness": 0.0, "policy_accuracy": 0.0, "severity_accuracy": 0.0,
                "false_positive_penalty": 0.0, "false_negative_penalty": 0.0, "total": 0.0,
                "feedback": f"Unknown post_id: {post_id}"}

    breakdown = compute_moderation_reward(
        predicted_decision=predicted_decision,
        predicted_policy=predicted_policy,
        predicted_severity=predicted_severity,
        ground_truth_decision=gt["decision"],
        ground_truth_policy=gt["policy_violated"],
        ground_truth_severity=gt["severity"],
    )

    # Build feedback string
    if breakdown["total"] == 1.0:
        feedback = f"Perfect decision for {post_id}."
    elif breakdown["correctness"] >= 1.0:
        feedback = f"Correct action for {post_id} but policy/severity needs refinement."
    elif breakdown["correctness"] > 0:
        feedback = (f"Adjacent decision for {post_id}. Expected '{gt['decision']}', "
                    f"got '{predicted_decision}'.")
    else:
        expected = gt["decision"]
        feedback = (f"Incorrect decision for {post_id}. Expected '{expected}', "
                    f"got '{predicted_decision}'. Policy: {gt['policy_violated']}.")

    breakdown["feedback"] = feedback
    breakdown["ground_truth_decision"] = gt["decision"]
    return breakdown

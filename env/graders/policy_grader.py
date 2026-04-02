"""
Grader for Task 2: policy_enforcement (Medium)
Higher weight on policy citation accuracy compared to spam task.
"""

import json
from pathlib import Path
from env.reward import compute_moderation_reward

DATA_PATH = Path(__file__).parent.parent / "data" / "policy_posts.json"


def load_ground_truth() -> dict:
    posts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {p["post_id"]: p["ground_truth"] for p in posts}


def grade_step(
    post_id: str,
    predicted_decision: str,
    predicted_policy: str | None,
    predicted_severity: str,
    ground_truth_map: dict,
) -> dict:
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

    # Policy enforcement weights policy accuracy MORE — override total
    # correctness 45%, policy 35%, severity 20%
    total = (
        0.45 * breakdown["correctness"]
        + 0.35 * breakdown["policy_accuracy"]
        + 0.20 * breakdown["severity_accuracy"]
        - 0.05 * breakdown["false_positive_penalty"]
        - 0.05 * breakdown["false_negative_penalty"]
    )
    breakdown["total"] = round(max(0.0, min(1.0, total)), 4)

    if breakdown["total"] >= 0.9:
        feedback = f"Excellent moderation decision for {post_id}."
    elif breakdown["correctness"] >= 1.0 and breakdown["policy_accuracy"] < 0.5:
        feedback = (f"Correct action for {post_id} but wrong policy cited. "
                    f"Expected: '{gt['policy_violated']}'.")
    elif breakdown["correctness"] > 0:
        feedback = (f"Partially correct for {post_id}. Expected '{gt['decision']}', "
                    f"got '{predicted_decision}'.")
    else:
        feedback = (f"Incorrect for {post_id}. Expected '{gt['decision']}' "
                    f"citing '{gt['policy_violated']}', severity '{gt['severity']}'.")

    breakdown["feedback"] = feedback
    breakdown["ground_truth_decision"] = gt["decision"]
    return breakdown

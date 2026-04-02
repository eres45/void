"""
Reward function for TrustGuard-Env.
Computes per-step rewards across all task types with rich partial credit signals.
"""

from typing import Optional


# Decision adjacency map — how "close" decisions are to each other
DECISION_ADJACENCY = {
    ("remove", "escalate"): 0.6,
    ("remove", "restrict_reach"): 0.4,
    ("remove", "age_gate"): 0.3,
    ("restrict_reach", "age_gate"): 0.6,
    ("restrict_reach", "remove"): 0.4,
    ("approve", "age_gate"): 0.4,
    ("approve", "request_context"): 0.3,
    ("escalate", "remove"): 0.6,
    ("escalate", "restrict_reach"): 0.4,
    ("age_gate", "restrict_reach"): 0.6,
    ("age_gate", "approve"): 0.4,
}

SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


def get_adjacency_score(predicted: str, ground_truth: str) -> float:
    """Returns partial credit for adjacent (but not exact) decisions."""
    if predicted == ground_truth:
        return 1.0
    score = DECISION_ADJACENCY.get((predicted, ground_truth), 0.0)
    score = max(score, DECISION_ADJACENCY.get((ground_truth, predicted), 0.0))
    return score


def severity_score(predicted: str, ground_truth: str) -> float:
    """Score severity accuracy with partial credit for adjacent severity ratings."""
    if predicted == ground_truth:
        return 1.0
    pred_idx = SEVERITY_ORDER.index(predicted) if predicted in SEVERITY_ORDER else 0
    gt_idx = SEVERITY_ORDER.index(ground_truth) if ground_truth in SEVERITY_ORDER else 0
    distance = abs(pred_idx - gt_idx)
    if distance == 1:
        return 0.5
    return 0.0


def compute_moderation_reward(
    predicted_decision: str,
    predicted_policy: Optional[str],
    predicted_severity: str,
    ground_truth_decision: str,
    ground_truth_policy: Optional[str],
    ground_truth_severity: str,
) -> dict:
    """
    Compute reward for a single post moderation decision.

    Returns a dict with breakdown and total score (0.0–1.0).
    """
    correct = get_adjacency_score(predicted_decision, ground_truth_decision)
    pol_acc = 0.0
    if ground_truth_policy is None:
        # No violation expected — policy field should be null
        pol_acc = 1.0 if predicted_policy is None else 0.3
    else:
        if predicted_policy == ground_truth_policy:
            pol_acc = 1.0
        elif predicted_policy is not None and predicted_policy.split("_policy")[0] == ground_truth_policy.split("_policy")[0]:
            pol_acc = 0.5  # right policy category, wrong sub-section
        else:
            pol_acc = 0.0

    sev_acc = severity_score(predicted_severity, ground_truth_severity)

    # False positive penalty (removing content that should be approved)
    fp_penalty = 0.0
    if predicted_decision == "remove" and ground_truth_decision == "approve":
        fp_penalty = 0.4
    elif predicted_decision in ("restrict_reach", "age_gate") and ground_truth_decision == "approve":
        fp_penalty = 0.2

    # False negative penalty (approving content that should be removed)
    fn_penalty = 0.0
    if predicted_decision == "approve" and ground_truth_decision == "remove":
        fn_penalty = 0.5
    elif predicted_decision == "approve" and ground_truth_decision in ("restrict_reach", "escalate"):
        fn_penalty = 0.3

    # Weighted total — correctness is primary signal
    total = (
        0.50 * correct
        + 0.25 * pol_acc
        + 0.15 * sev_acc
        - 0.05 * fp_penalty
        - 0.05 * fn_penalty
    )
    total = round(max(0.0, min(1.0, total)), 4)

    return {
        "correctness": round(correct, 4),
        "policy_accuracy": round(pol_acc, 4),
        "severity_accuracy": round(sev_acc, 4),
        "false_positive_penalty": round(fp_penalty, 4),
        "false_negative_penalty": round(fn_penalty, 4),
        "total": total,
    }


def compute_appeal_reward(
    predicted_decision: str,
    ground_truth_decision: str,
) -> dict:
    """
    Compute reward for an appeal review decision.
    Adjacent decisions get partial credit.
    """
    APPEAL_ADJACENCY = {
        ("uphold", "modify_restrict"): 0.4,
        ("uphold", "modify_age_gate"): 0.4,
        ("overturn", "modify_restrict"): 0.4,
        ("overturn", "modify_age_gate"): 0.4,
        ("modify_restrict", "modify_age_gate"): 0.6,
        ("modify_restrict", "uphold"): 0.4,
        ("modify_restrict", "overturn"): 0.4,
        ("modify_age_gate", "modify_restrict"): 0.6,
        ("modify_age_gate", "uphold"): 0.4,
        ("modify_age_gate", "overturn"): 0.4,
    }

    if predicted_decision == ground_truth_decision:
        correctness = 1.0
    else:
        correctness = APPEAL_ADJACENCY.get((predicted_decision, ground_truth_decision), 0.0)

    total = round(max(0.0, min(1.0, correctness)), 4)
    return {"correctness": correctness, "total": total}


def compute_cib_reward(
    flagged_accounts: list,
    true_cib_accounts: list,
    all_accounts: list,
) -> dict:
    """
    Compute F1-based reward for CIB network detection.
    Precision + Recall equally weighted.
    """
    true_set = set(true_cib_accounts)
    flagged_set = set(flagged_accounts)
    all_set = set(all_accounts)

    tp = len(flagged_set & true_set)
    fp = len(flagged_set - true_set)
    fn = len(true_set - flagged_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "score": round(f1, 4),
        "correct_flags": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "total_true_cib": len(true_set),
        "total_flagged": len(flagged_set),
    }

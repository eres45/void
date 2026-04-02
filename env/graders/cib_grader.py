"""
Grader for Task 3: coordinated_inauthentic_behavior (Hard)
F1-based grading on network detection accuracy.
"""

import json
from pathlib import Path
from env.reward import compute_cib_reward

DATA_PATH = Path(__file__).parent.parent / "data" / "cib_scenarios.json"


def load_scenario() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def grade(
    account_decisions: dict,
    scenario: dict,
) -> dict:
    """
    Grade the CIB detection result.

    Args:
        account_decisions: dict mapping account_id -> "flag_cib" | "clear" | "investigate_further"
        scenario: loaded CIB scenario dict

    Returns:
        Reward breakdown dict
    """
    true_cib = set(scenario["true_cib_accounts"])
    all_accounts = [acc["account_id"] for acc in scenario["accounts"]]

    # "flag_cib" counts as flagged; "investigate_further" gives half credit
    flagged_full = [aid for aid, dec in account_decisions.items() if dec == "flag_cib"]
    flagged_partial = [aid for aid, dec in account_decisions.items() if dec == "investigate_further"]

    # Grant half-credit for "investigate_further" on true CIB accounts
    partial_tp = len([a for a in flagged_partial if a in true_cib]) * 0.5
    partial_fp = len([a for a in flagged_partial if a not in true_cib]) * 0.5

    result = compute_cib_reward(flagged_full, list(true_cib), all_accounts)

    # Adjust for partial credit from "investigate_further"
    tp = result["correct_flags"] + partial_tp
    fp = result["false_positives"] + partial_fp
    fn = result["false_negatives"] - partial_tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    if f1 >= 0.9:
        feedback = "Excellent CIB detection — correctly identified the coordinated network."
    elif f1 >= 0.6:
        feedback = f"Good detection. Missed {int(fn)} CIB accounts or had {int(fp)} false positives."
    elif f1 >= 0.3:
        feedback = f"Partial detection. True CIB accounts: {list(true_cib)}."
    else:
        feedback = f"Poor detection. True CIB accounts were: {list(true_cib)}."

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "score": round(f1, 4),
        "correct_flags": result["correct_flags"],
        "false_positives": result["false_positives"],
        "false_negatives": result["false_negatives"],
        "total_true_cib": len(true_cib),
        "total_flagged": len(flagged_full),
        "feedback": feedback,
    }

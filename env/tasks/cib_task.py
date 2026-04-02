"""
Task 3: coordinated_inauthentic_behavior (Hard)
Agent investigates accounts and detects a coordinated network.
Single-step task: agent receives all data and returns decisions for all accounts.

Supports 3 different CIB scenarios (anti-EU, vaccine disinfo, crypto pump)
to prevent memorization/exploitation.
"""

import json
from pathlib import Path
from env.graders import cib_grader

DATA_PATH = Path(__file__).parent.parent / "data" / "cib_scenarios.json"
POLICIES_PATH = Path(__file__).parent.parent / "data" / "policies.json"

TASK_INSTRUCTIONS = (
    "You are a Trust & Safety investigator specializing in coordinated inauthentic behavior (CIB). "
    "You have been given data on multiple accounts that have been posting about the same topic. "
    "Analyze posting patterns, timing, cross-references, language similarity, account age, "
    "and follower/following ratios to identify which accounts, if any, are part of a "
    "coordinated inauthentic network. "
    "For EACH account, decide: 'flag_cib' (part of network), 'clear' (legitimate), or "
    "'investigate_further' (suspicious but insufficient evidence). "
    "You must provide decisions for ALL accounts listed. "
    "Key CIB signals: new accounts (< 30 days) posting at high frequency (> 10/day), "
    "cross-tagging the same accounts repeatedly, identical or near-identical messaging, "
    "synchronized posting times, low follower counts with high following counts."
)


class CIBTask:
    def __init__(self, scenario_index: int = 0):
        all_scenarios = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        # Support both old single-object format and new list format
        if isinstance(all_scenarios, list):
            self.scenario = all_scenarios[scenario_index % len(all_scenarios)]
        else:
            self.scenario = all_scenarios
        self.policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
        self.reset()

    def reset(self) -> dict:
        self.done = False
        self.scores = []
        self.result = None
        return self._make_observation()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        """
        Single step: agent submits decisions for all accounts.
        action["account_decisions"]: dict of {account_id: decision}
        """
        if self.done:
            raise RuntimeError("Episode already done. Call reset() first.")

        account_decisions = action.get("account_decisions", {})
        result = cib_grader.grade(account_decisions, self.scenario)

        self.result = result
        self.scores = [result["score"]]
        self.done = True

        reward = {
            "step": 1,
            "score": result["score"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f1_score": result["f1_score"],
            "correct_flags": result["correct_flags"],
            "false_positives": result["false_positives"],
            "false_negatives": result["false_negatives"],
            "total_true_cib": result["total_true_cib"],
            "total_flagged": result["total_flagged"],
            "feedback": result["feedback"],
            "cumulative_score": result["score"],
            "done": True,
        }

        info = {"task": "coordinated_inauthentic_behavior", "step": 1, "total_steps": 1}
        return None, reward, True, info

    def state(self) -> dict:
        return {
            "task_name": "coordinated_inauthentic_behavior",
            "current_step": 1 if self.done else 0,
            "total_steps": 1,
            "cumulative_score": self.scores[0] if self.scores else 0.0,
            "done": self.done,
            "scores_per_step": self.scores,
            "items_processed": 1 if self.done else 0,
            "items_correct": 1 if (self.scores and self.scores[0] >= 0.7) else 0,
        }

    def _make_observation(self) -> dict:
        cib_policy_texts = [
            f"cib_policy_10.1: {self.policies['cib_policy_10.1']}",
            f"cib_policy_10.2: {self.policies['cib_policy_10.2']}",
        ]
        account_ids = [acc["account_id"] for acc in self.scenario["accounts"]]
        return {
            "task_name": "coordinated_inauthentic_behavior",
            "scenario_id": self.scenario.get("scenario_id", "cib_001"),
            "step": 0,
            "total_steps": 1,
            "accounts": self.scenario["accounts"],
            "account_ids_to_classify": account_ids,
            "time_window_hours": self.scenario["time_window_hours"],
            "narrative_topic": self.scenario["narrative_topic"],
            "policy_sections": cib_policy_texts,
            "instructions": TASK_INSTRUCTIONS,
        }

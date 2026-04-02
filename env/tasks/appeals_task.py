"""
Task 4: appeal_review (Medium)
Agent reviews 8 user appeals against previous moderation decisions.
"""

import json
from pathlib import Path
from env.graders import appeals_grader

DATA_PATH = Path(__file__).parent.parent / "data" / "appeals.json"
POLICIES_PATH = Path(__file__).parent.parent / "data" / "policies.json"

TASK_INSTRUCTIONS = (
    "You are an appeals reviewer at a social media platform. "
    "A user has appealed a previous moderation decision. "
    "Review the original post, the original decision, the user's appeal argument, "
    "and any new evidence provided. Decide whether to: "
    "'uphold' (keep the original removal — violation stands), "
    "'overturn' (reverse the decision — restore content), "
    "'modify_restrict' (downgrade from removal to restrict_reach), or "
    "'modify_age_gate' (downgrade from removal to age_gate). "
    "New evidence and context should be carefully weighed. "
    "User account history and prior violations are relevant to your decision."
)

APPEAL_RELEVANT_POLICIES = [
    "hate_speech_policy_2.3",
    "satire_exemption_3.4",
    "health_misinformation_4.1",
    "misinformation_policy_4.1",
    "privacy_policy_5.1",
    "illegal_goods_policy_7.3",
    "self_harm_policy_8.1",
    "nudity_policy_9.2",
    "spam_policy_1.3",
]


class AppealsTask:
    def __init__(self):
        self.appeals = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
        self.ground_truth_map = appeals_grader.load_ground_truth()
        self.reset()

    def reset(self) -> dict:
        self.current_index = 0
        self.scores = []
        self.done = False
        return self._make_observation()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        appeal_id = self.appeals[self.current_index]["appeal_id"]

        result = appeals_grader.grade_step(
            appeal_id=appeal_id,
            predicted_decision=action.get("decision", "uphold"),
            predicted_reasoning=action.get("reasoning", ""),
            ground_truth_map=self.ground_truth_map,
        )

        step_score = result["total"]
        self.scores.append(step_score)
        self.current_index += 1
        self.done = self.current_index >= len(self.appeals)

        cumulative = sum(self.scores) / len(self.scores)

        reward = {
            "step": len(self.scores),
            "appeal_id": appeal_id,
            "score": step_score,
            "correctness": result["correctness"],
            "feedback": result["feedback"],
            "cumulative_score": round(cumulative, 4),
            "done": self.done,
        }

        obs = None if self.done else self._make_observation()
        info = {"task": "appeal_review", "step": len(self.scores), "total_steps": len(self.appeals)}
        return obs, reward, self.done, info

    def state(self) -> dict:
        return {
            "task_name": "appeal_review",
            "current_step": self.current_index,
            "total_steps": len(self.appeals),
            "cumulative_score": round(sum(self.scores) / len(self.scores), 4) if self.scores else 0.0,
            "done": self.done,
            "scores_per_step": self.scores,
            "items_processed": self.current_index,
            "items_correct": sum(1 for s in self.scores if s >= 0.8),
        }

    def _make_observation(self) -> dict:
        appeal = self.appeals[self.current_index]
        policy_texts = [
            f"{pid}: {self.policies[pid]}"
            for pid in APPEAL_RELEVANT_POLICIES
            if pid in self.policies
        ]
        return {
            "task_name": "appeal_review",
            "appeal_id": appeal["appeal_id"],
            "step": self.current_index + 1,
            "original_post_content": appeal["original_post_content"],
            "original_decision": appeal["original_decision"],
            "original_policy_cited": appeal.get("original_policy_cited"),
            "appeal_argument": appeal["appeal_argument"],
            "new_evidence": appeal.get("new_evidence"),
            "user_history": appeal["user"],
            "policy_sections": policy_texts,
            "queue_remaining": len(self.appeals) - self.current_index - 1,
            "instructions": TASK_INSTRUCTIONS,
        }

"""
Task 2: policy_enforcement (Medium)
Agent enforces platform policies on 12 contextually ambiguous posts.
"""

import json
from pathlib import Path
from env.graders import policy_grader

DATA_PATH = Path(__file__).parent.parent / "data" / "policy_posts.json"
POLICIES_PATH = Path(__file__).parent.parent / "data" / "policies.json"

TASK_INSTRUCTIONS = (
    "You are a senior content moderator handling nuanced policy cases. "
    "Review each post carefully, considering the full context, user history, "
    "and account type. Use the full action set: 'approve', 'remove', "
    "'restrict_reach', 'age_gate', 'escalate', or 'request_context'. "
    "You MUST cite the specific policy ID for any violation (e.g. 'hate_speech_policy_2.1'). "
    "Severity ratings: none, low, medium, high, critical. "
    "Context and user history are critical — the same content may require "
    "different decisions based on who posted it and why."
)

POLICY_RELEVANT_POLICIES = [
    "hate_speech_policy_2.1", "hate_speech_policy_2.2", "hate_speech_policy_2.3",
    "satire_exemption_3.4",
    "health_misinformation_4.1", "health_misinformation_4.2",
    "misinformation_policy_4.1",
    "privacy_policy_5.1", "privacy_policy_5.2",
    "newsworthiness_exemption_6.1",
    "illegal_goods_policy_7.3",
    "self_harm_policy_8.1", "self_harm_policy_8.2",
    "nudity_policy_9.1", "nudity_policy_9.2",
    "spam_policy_1.2",
]


class PolicyTask:
    def __init__(self):
        self.posts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
        self.ground_truth_map = policy_grader.load_ground_truth()
        self.reset()

    def reset(self) -> dict:
        self.current_index = 0
        self.scores = []
        self.done = False
        return self._make_observation()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        post_id = self.posts[self.current_index]["post_id"]

        result = policy_grader.grade_step(
            post_id=post_id,
            predicted_decision=action.get("decision", "approve"),
            predicted_policy=action.get("policy_violated"),
            predicted_severity=action.get("severity", "none"),
            ground_truth_map=self.ground_truth_map,
        )

        step_score = result["total"]
        self.scores.append(step_score)
        self.current_index += 1
        self.done = self.current_index >= len(self.posts)

        cumulative = sum(self.scores) / len(self.scores)

        reward = {
            "step": len(self.scores),
            "post_id": post_id,
            "score": step_score,
            "correctness": result["correctness"],
            "policy_accuracy": result["policy_accuracy"],
            "severity_accuracy": result["severity_accuracy"],
            "feedback": result["feedback"],
            "cumulative_score": round(cumulative, 4),
            "done": self.done,
        }

        obs = None if self.done else self._make_observation()
        info = {"task": "policy_enforcement", "step": len(self.scores), "total_steps": len(self.posts)}
        return obs, reward, self.done, info

    def state(self) -> dict:
        return {
            "task_name": "policy_enforcement",
            "current_step": self.current_index,
            "total_steps": len(self.posts),
            "cumulative_score": round(sum(self.scores) / len(self.scores), 4) if self.scores else 0.0,
            "done": self.done,
            "scores_per_step": self.scores,
            "items_processed": self.current_index,
            "items_correct": sum(1 for s in self.scores if s >= 0.7),
        }

    def _make_observation(self) -> dict:
        post = self.posts[self.current_index]
        policy_texts = [
            f"{pid}: {self.policies[pid]}"
            for pid in POLICY_RELEVANT_POLICIES
            if pid in self.policies
        ]
        return {
            "task_name": "policy_enforcement",
            "step": self.current_index + 1,
            "post_id": post["post_id"],
            "content": post["content"],
            "user_history": post["user"],
            "engagement": post["engagement"],
            "context": post.get("context"),
            "policy_sections": policy_texts,
            "queue_remaining": len(self.posts) - self.current_index - 1,
            "instructions": TASK_INSTRUCTIONS,
        }

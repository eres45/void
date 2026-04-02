"""
Task 1: spam_detection (Easy)
Agent reviews 15 posts and identifies spam vs. legitimate content.
"""

import json
from pathlib import Path
from env.graders import spam_grader

DATA_PATH = Path(__file__).parent.parent / "data" / "spam_posts.json"
POLICIES_PATH = Path(__file__).parent.parent / "data" / "policies.json"

TASK_INSTRUCTIONS = (
    "You are a content moderator. Review the post and choose one action: "
    "'approve' (content is fine), 'remove' (clear policy violation), "
    "'restrict_reach' (reduce distribution), 'age_gate' (adults only), "
    "'escalate' (specialist review needed), 'request_context' (need more info). "
    "Cite the specific policy ID if you find a violation (e.g. 'spam_policy_1.2'). "
    "Rate severity as: none, low, medium, high, or critical."
)

SPAM_RELEVANT_POLICIES = [
    "spam_policy_1.1",
    "spam_policy_1.2",
    "spam_policy_1.3",
    "health_misinformation_4.1",
]


class SpamTask:
    def __init__(self):
        self.posts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
        self.ground_truth_map = spam_grader.load_ground_truth()
        self.reset()

    def reset(self) -> dict:
        self.current_index = 0
        self.scores = []
        self.done = False
        return self._make_observation()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        """Process one moderation decision. Returns (obs, reward, done, info)."""
        post_id = self.posts[self.current_index]["post_id"]

        result = spam_grader.grade_step(
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
        info = {"task": "spam_detection", "step": len(self.scores), "total_steps": len(self.posts)}
        return obs, reward, self.done, info

    def state(self) -> dict:
        return {
            "task_name": "spam_detection",
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
            for pid in SPAM_RELEVANT_POLICIES
            if pid in self.policies
        ]
        return {
            "task_name": "spam_detection",
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

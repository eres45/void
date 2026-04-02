"""
TrustGuard-Env — Main Environment Class
Implements the full OpenEnv spec: step() / reset() / state()
"""

from env.tasks.spam_task import SpamTask
from env.tasks.policy_task import PolicyTask
from env.tasks.cib_task import CIBTask
from env.tasks.appeals_task import AppealsTask

TASK_REGISTRY = {
    "spam_detection": SpamTask,
    "policy_enforcement": PolicyTask,
    "coordinated_inauthentic_behavior": CIBTask,
    "appeal_review": AppealsTask,
}

VALID_TASKS = list(TASK_REGISTRY.keys())


class TrustGuardEnv:
    """
    TrustGuardEnv — Real-world Trust & Safety OpenEnv environment.

    Simulates social media content moderation workflows including:
    - Spam detection (easy)
    - Policy enforcement on nuanced content (medium)
    - Coordinated inauthentic behavior detection (hard)
    - User appeal review (medium)

    Usage:
        env = TrustGuardEnv()
        obs = env.reset("spam_detection")
        obs, reward, done, info = env.step(action)
        state = env.state()
    """

    def __init__(self):
        self._task = None
        self._task_name = None

    def reset(self, task_name: str = "spam_detection") -> dict:
        """
        Initialize a new episode for the given task.

        Args:
            task_name: One of 'spam_detection', 'policy_enforcement',
                       'coordinated_inauthentic_behavior', 'appeal_review'

        Returns:
            Initial observation dict
        """
        if task_name not in TASK_REGISTRY:
            raise ValueError(
                f"Unknown task '{task_name}'. Valid tasks: {VALID_TASKS}"
            )
        self._task_name = task_name
        self._task = TASK_REGISTRY[task_name]()
        return self._task.reset()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        """
        Execute one step in the environment.

        Args:
            action: Dict containing the agent's decision. Structure varies by task:
                - spam_detection / policy_enforcement:
                    {"post_id": str, "decision": str, "policy_violated": str|null,
                     "severity": str, "reasoning": str}
                - coordinated_inauthentic_behavior:
                    {"account_decisions": {account_id: decision}, "reasoning": str}
                - appeal_review:
                    {"appeal_id": str, "decision": str, "reasoning": str}

        Returns:
            (observation, reward, done, info)
            observation: next state (None if done)
            reward: dict with score breakdown
            done: whether episode is complete
            info: metadata dict
        """
        if self._task is None:
            raise RuntimeError("Environment not initialized. Call reset(task_name) first.")
        return self._task.step(action)

    def state(self) -> dict:
        """
        Return current episode state.

        Returns:
            Dict with task_name, current_step, total_steps, cumulative_score,
            done, scores_per_step, items_processed, items_correct
        """
        if self._task is None:
            return {
                "task_name": None,
                "current_step": 0,
                "total_steps": 0,
                "cumulative_score": 0.0,
                "done": False,
                "scores_per_step": [],
                "items_processed": 0,
                "items_correct": 0,
            }
        return self._task.state()

    @staticmethod
    def list_tasks() -> list[str]:
        """Return list of all available task names."""
        return VALID_TASKS

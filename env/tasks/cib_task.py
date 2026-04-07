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
    "You are a Trust & Safety investigator specialized in Coordinated Inauthentic Behavior (CIB). "
    "You are analyzing a set of accounts for potential automated or coordinated manipulation. "
    "Initially, you only see basic account metadata (age, followers, following). "
    "\n\nINVESTIGATION TOOLS:\n"
    "- 'view_posts': Unlocks account bio, recent posts, and top hashtags.\n"
    "- 'view_metadata': Unlocks average posting hour and posts per day frequency.\n"
    "- 'view_network': Unlocks cross-tagged accounts and network mentions.\n\n"
    "ACTIONS:\n"
    "1. 'investigate': Use a tool on a specific account to unlock more data.\n"
    "2. 'submit': Provide your final classification for ALL accounts once you have sufficient evidence. "
    "Decisions: 'flag_cib', 'clear', or 'investigate_further'.\n\n"
    "Strategy: Investigation actions take a step but provide critical evidence. "
    "Efficiency matters — don't over-investigate if the signals are clear."
)


class CIBTask:
    def __init__(self, scenario_index: int = 0):
        all_scenarios = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(all_scenarios, list):
            self.scenario = all_scenarios[scenario_index % len(all_scenarios)]
        else:
            self.scenario = all_scenarios
        self.policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
        
        # State tracking
        self.current_step = 0
        self.max_steps = 10
        self.revealed_data = {acc["account_id"]: set() for acc in self.scenario["accounts"]}
        self.done = False
        self.scores = []
        self.last_result_msg = "Investigation started."
        
        self.reset()

    def reset(self) -> dict:
        self.current_step = 0
        self.done = False
        self.scores = []
        self.revealed_data = {acc["account_id"]: set() for acc in self.scenario["accounts"]}
        self.last_result_msg = "Investigation started."
        return self._make_observation()

    def step(self, action: dict) -> tuple[dict | None, dict, bool, dict]:
        if self.done:
            raise RuntimeError("Episode already done.")

        action_type = action.get("action_type")
        self.current_step += 1
        
        if action_type == "investigate":
            target_id = action.get("target_account_id")
            tool = action.get("investigation_tool")
            
            if target_id not in self.revealed_data:
                self.last_result_msg = f"Error: Account {target_id} not found."
                step_score = 0.0
            elif tool not in ["view_posts", "view_network", "view_metadata"]:
                self.last_result_msg = f"Error: Invalid tool {tool}."
                step_score = 0.0
            else:
                self.revealed_data[target_id].add(tool)
                self.last_result_msg = f"Successfully used {tool} on {target_id}."
                step_score = 0.01  # Small nudge for investigative activity
            
            self.scores.append(step_score)
            
            if self.current_step >= self.max_steps:
                # Force submission with empty decisions if they ran out of steps
                action_type = "submit"
                action["account_decisions"] = {aid: "clear" for aid in self.revealed_data.keys()}
            else:
                obs = self._make_observation()
                reward = {
                    "step": self.current_step,
                    "score": step_score,
                    "feedback": self.last_result_msg,
                    "cumulative_score": sum(self.scores) / len(self.scores),
                    "done": False,
                }
                return obs, reward, False, {"task": "cib", "step": self.current_step}

        if action_type == "submit":
            decisions = action.get("account_decisions", {})
            result = cib_grader.grade(decisions, self.scenario)
            
            self.scores.append(result["score"])
            self.done = True
            
            reward = {
                "step": self.current_step,
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
                "cumulative_score": sum(self.scores) / len(self.scores),
                "done": True,
            }
            return None, reward, True, {"task": "cib", "step": self.current_step}

        # Fallback for invalid action_type
        return self._make_observation(), {"score": 0, "feedback": "Invalid action", "done": False}, False, {}

    def state(self) -> dict:
        return {
            "task_name": "coordinated_inauthentic_behavior",
            "current_step": self.current_step,
            "total_steps": self.max_steps,
            "cumulative_score": sum(self.scores) / len(self.scores) if self.scores else 0.0,
            "done": self.done,
            "scores_per_step": self.scores,
            "items_processed": 1 if self.done else 0,
            "items_correct": 1 if (self.done and self.scores[-1] >= 0.7) else 0,
        }

    def _make_observation(self) -> dict:
        obs_accounts = []
        for acc in self.scenario["accounts"]:
            aid = acc["account_id"]
            revealed = self.revealed_data[aid]
            
            # Base data always visible
            obs_acc = {
                "account_id": aid,
                "username": acc["username"],
                "account_age_days": acc["account_age_days"],
                "follower_count": acc["follower_count"],
                "following_count": acc["following_count"],
            }
            
            # Conditional data
            if "view_posts" in revealed:
                obs_acc.update({
                    "bio": acc["bio"],
                    "posts": acc["posts"],
                    "hashtags_used": acc["hashtags_used"],
                })
            if "view_metadata" in revealed:
                obs_acc.update({
                    "avg_posting_hour": acc["avg_posting_hour"],
                    "posts_per_day": acc["posts_per_day"],
                })
            if "view_network" in revealed:
                obs_acc.update({
                    "cross_tagged_accounts": acc["cross_tagged_accounts"],
                })
            
            obs_accounts.append(obs_acc)

        cib_policy_texts = [
            f"cib_policy_10.1: {self.policies['cib_policy_10.1']}",
            f"cib_policy_10.2: {self.policies['cib_policy_10.2']}",
        ]

        return {
            "task_name": "coordinated_inauthentic_behavior",
            "scenario_id": self.scenario.get("scenario_id", "cib_001"),
            "step": self.current_step,
            "total_steps": self.max_steps,
            "accounts": obs_accounts,
            "account_ids_to_classify": [a["account_id"] for a in self.scenario["accounts"]],
            "time_window_hours": self.scenario["time_window_hours"],
            "narrative_topic": self.scenario["narrative_topic"],
            "policy_sections": cib_policy_texts,
            "instructions": TASK_INSTRUCTIONS,
            "last_action_result": self.last_result_msg
        }

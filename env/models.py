"""
TrustGuard-Env — Pydantic Models
All typed models for Observation, Action, and Reward per OpenEnv spec.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class UserHistory(BaseModel):
    account_age_days: int = Field(description="Age of the account in days")
    previous_violations: int = Field(description="Number of past policy violations")
    follower_count: int = Field(description="Number of followers")
    is_verified: bool = Field(description="Whether the account is platform-verified")
    account_type: Literal["personal", "business", "creator", "press", "bot_suspected"]


class EngagementMetrics(BaseModel):
    views: int = Field(description="Total view count on the post")
    likes: int = Field(description="Total like count")
    shares: int = Field(description="Total share count")
    comments: int = Field(description="Total comment count")
    report_count: int = Field(description="Number of user reports received")


# ---------------------------------------------------------------------------
# Task 1 & 2: Post Moderation Models
# ---------------------------------------------------------------------------

class PostObservation(BaseModel):
    """Observation returned per step for spam_detection and policy_enforcement tasks."""
    task_name: str
    step: int = Field(description="Current step number (1-indexed)")
    post_id: str
    content: str = Field(description="The full text content of the post")
    user_history: UserHistory
    engagement: EngagementMetrics
    context: Optional[str] = Field(None, description="Extra context: thread, account bio, verified source info")
    policy_sections: List[str] = Field(description="Relevant policy excerpts to guide decision")
    queue_remaining: int = Field(description="Number of posts remaining in queue after this one")
    instructions: str = Field(description="Task instructions reminding agent of available actions")


class ModerationAction(BaseModel):
    """Agent's moderation decision for a single post (Tasks 1 & 2)."""
    post_id: str
    decision: Literal[
        "approve",         # Content is fine, no action needed
        "remove",          # Remove content — clear policy violation
        "restrict_reach",  # Reduce algorithmic distribution without removal
        "age_gate",        # Restrict to 18+ audiences only
        "escalate",        # Escalate to specialist human review team
        "request_context"  # Insufficient info — request more context
    ]
    policy_violated: Optional[str] = Field(
        None,
        description="The specific policy ID violated (e.g. 'hate_speech_policy_2.1'). Null if approving."
    )
    severity: Literal["none", "low", "medium", "high", "critical"]
    reasoning: str = Field(description="Clear explanation of the moderation decision")


class StepReward(BaseModel):
    """Per-step reward returned after each moderation decision (Tasks 1, 2, 4)."""
    step: int
    post_id: str
    score: float = Field(ge=0.0, le=1.0, description="Score for this step (0.0–1.0)")
    correctness: float = Field(ge=0.0, le=1.0, description="Was the decision correct?")
    policy_accuracy: float = Field(ge=0.0, le=1.0, description="Was the correct policy cited?")
    severity_accuracy: float = Field(ge=0.0, le=1.0, description="Was severity rated correctly?")
    feedback: str = Field(description="Human-readable feedback on the decision")
    cumulative_score: float = Field(ge=0.0, le=1.0, description="Running average score")
    done: bool = Field(description="Whether the episode is complete")


# ---------------------------------------------------------------------------
# Task 3: Coordinated Inauthentic Behavior (CIB) Models
# ---------------------------------------------------------------------------

class AccountObservation(BaseModel):
    """Profile + behavioral data for a single account in CIB investigation."""
    account_id: str
    username: str
    bio: str
    account_age_days: int
    follower_count: int
    following_count: int
    posts: List[str] = Field(description="Recent post contents by this account")
    hashtags_used: List[str] = Field(description="Top hashtags used across posts")
    avg_posting_hour: float = Field(description="Average posting hour (0–23 scale)")
    posts_per_day: float = Field(description="Average posts per day")
    cross_tagged_accounts: List[str] = Field(description="Other accounts this account tags or mentions")


class CIBObservation(BaseModel):
    """Full investigation batch for coordinated_inauthentic_behavior task."""
    task_name: str = "coordinated_inauthentic_behavior"
    step: int = 0
    total_steps: int = 1
    accounts: List[AccountObservation]
    time_window_hours: int = Field(description="Duration of the behavior window being analyzed")
    narrative_topic: str = Field(description="The narrative or topic observed across posts")
    instructions: str = Field(description="Task instructions for the agent")


class CIBAction(BaseModel):
    """Agent's classification decisions across all accounts in the CIB investigation."""
    account_decisions: Dict[str, Literal["flag_cib", "clear", "investigate_further"]] = Field(
        description="Map of account_id → decision for every account in the investigation"
    )
    network_description: Optional[str] = Field(
        None,
        description="Description of the CIB network identified (if any)"
    )
    reasoning: str = Field(description="Overall reasoning across all accounts")


class CIBReward(BaseModel):
    """Reward for the single-step CIB task."""
    step: int = 0
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    correct_flags: int
    false_positives: int
    false_negatives: int
    total_true_cib: int
    total_flagged: int
    feedback: str
    cumulative_score: float
    done: bool = True


# ---------------------------------------------------------------------------
# Task 4: Appeal Review Models
# ---------------------------------------------------------------------------

class AppealObservation(BaseModel):
    """Observation for a single appeal review (Task 4)."""
    task_name: str = "appeal_review"
    appeal_id: str
    step: int
    original_post_content: str = Field(description="The content of the originally moderated post")
    original_decision: str = Field(description="The original moderation decision that was made")
    original_policy_cited: Optional[str] = Field(None, description="Policy cited in original decision")
    appeal_argument: str = Field(description="The user's appeal argument")
    new_evidence: Optional[str] = Field(None, description="Any new evidence or context provided in the appeal")
    user_history: UserHistory
    policy_sections: List[str] = Field(description="Relevant policy excerpts")
    queue_remaining: int
    instructions: str = Field(description="Task instructions for the agent")


class AppealAction(BaseModel):
    """Agent's decision on a user appeal."""
    appeal_id: str
    decision: Literal[
        "uphold",           # Maintain the original removal — violation stands
        "overturn",         # Reverse decision, restore content — no violation
        "modify_restrict",  # Downgrade: change removal to restrict_reach
        "modify_age_gate"   # Downgrade: change removal to age_gate
    ]
    reasoning: str = Field(description="Reasoning for the appeal decision")
    policy_cited: Optional[str] = Field(None, description="Policy supporting the decision")


class AppealReward(BaseModel):
    """Per-step reward for appeal review task."""
    step: int
    appeal_id: str
    score: float = Field(ge=0.0, le=1.0)
    correctness: float = Field(ge=0.0, le=1.0)
    feedback: str
    cumulative_score: float
    done: bool


# ---------------------------------------------------------------------------
# Task State & API Response Models
# ---------------------------------------------------------------------------

class TaskState(BaseModel):
    """Returned by state() endpoint."""
    task_name: str
    current_step: int
    total_steps: int
    cumulative_score: float
    done: bool
    scores_per_step: List[float]
    items_processed: int
    items_correct: int


class ResetResponse(BaseModel):
    observation: Dict[str, Any]
    task_name: str
    total_steps: int
    message: str


class StepResponse(BaseModel):
    observation: Optional[Dict[str, Any]] = None
    reward: Dict[str, Any]
    done: bool
    info: Dict[str, Any]

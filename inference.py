"""
TrustGuard-Env — Baseline Inference Script
Runs a language model against all 4 tasks using the OpenAI API client.

Required environment variables:
  API_BASE_URL  - The API endpoint for the LLM
  MODEL_NAME    - The model identifier to use
  HF_TOKEN      - Your Hugging Face / API key (used as OpenAI API key)

Usage:
  python inference.py

Output: Structured stdout logs in [START] / [STEP] / [END] format.
"""

import os
import json
import sys
import time
from datetime import datetime, timezone

from openai import OpenAI
from env.environment import TrustGuardEnv

# ---------------------------------------------------------------------------
# Configuration — loaded from environment variables (mandatory per spec)
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
# Optional — if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

if not HF_TOKEN:
    print("[ERROR] HF_TOKEN or OPENAI_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

# ---------------------------------------------------------------------------
# Log helpers — strict [START] / [STEP] / [END] format
# ---------------------------------------------------------------------------

def log_start(task: str, model: str):
    print(json.dumps({
        "event": "START",
        "task": task,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), flush=True)


def log_step(step: int, item_id: str, decision: str, score: float, cumulative: float, info: dict = None):
    record = {
        "event": "STEP",
        "step": step,
        "item_id": item_id,
        "decision": decision,
        "score": round(score, 4),
        "cumulative_score": round(cumulative, 4),
    }
    if info:
        record["info"] = info
    print(json.dumps(record), flush=True)


def log_end(task: str, total_score: float, steps: int, elapsed_seconds: float):
    print(json.dumps({
        "event": "END",
        "task": task,
        "total_score": round(total_score, 4),
        "steps": steps,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), flush=True)


# ---------------------------------------------------------------------------
# LLM prompting helpers
# ---------------------------------------------------------------------------

def build_moderation_prompt(obs: dict) -> str:
    return f"""You are a content moderator. Review the following post and make a moderation decision.

TASK: {obs.get('task_name', 'moderation')}
INSTRUCTIONS: {obs.get('instructions', '')}

POST ID: {obs['post_id']}
CONTENT: {obs['content']}

USER HISTORY:
- Account age: {obs['user_history']['account_age_days']} days
- Previous violations: {obs['user_history']['previous_violations']}
- Followers: {obs['user_history']['follower_count']}
- Verified: {obs['user_history']['is_verified']}
- Account type: {obs['user_history']['account_type']}

ENGAGEMENT:
- Views: {obs['engagement']['views']}, Likes: {obs['engagement']['likes']}
- Shares: {obs['engagement']['shares']}, Reports: {obs['engagement']['report_count']}

{f"CONTEXT: {obs['context']}" if obs.get('context') else ""}

RELEVANT POLICIES:
{chr(10).join(obs.get('policy_sections', [])[:5])}

Queue remaining: {obs.get('queue_remaining', 0)} posts after this one.

Respond ONLY with a JSON object in this exact format:
{{
  "post_id": "{obs['post_id']}",
  "decision": "<approve|remove|restrict_reach|age_gate|escalate|request_context>",
  "policy_violated": "<policy_id or null>",
  "severity": "<none|low|medium|high|critical>",
  "reasoning": "<brief explanation>"
}}"""


def build_cib_prompt(obs: dict) -> str:
    accounts_text = ""
    for acc in obs["accounts"]:
        accounts_text += f"""
ACCOUNT: {acc['account_id']} (@{acc['username']})
Age: {acc['account_age_days']} days | Followers: {acc['follower_count']} | Following: {acc['following_count']}
Unlocked Data: {', '.join([k for k, v in acc.items() if v is not None and k not in ['account_id', 'username', 'account_age_days', 'follower_count', 'following_count']]) or 'Basic metadata only'}
"""
        if acc.get("bio"): accounts_text += f"Bio: {acc['bio']}\n"
        if acc.get("posts"): accounts_text += f"Recent posts: {acc['posts'][:2]}\n"
        if acc.get("hashtags_used"): accounts_text += f"Hashtags: {acc['hashtags_used']}\n"
        if acc.get("posts_per_day"): accounts_text += f"Activity: {acc['posts_per_day']} posts/day | Avg hr: {acc['avg_posting_hour']}\n"
        if acc.get("cross_tagged_accounts"): accounts_text += f"Cross-tags: {acc['cross_tagged_accounts']}\n"

    return f"""You are a Trust & Safety investigator specializing in coordinated inauthentic behavior (CIB).

TASK: coordinated_inauthentic_behavior (Step {obs['step']}/{obs['total_steps']})
INSTRUCTIONS: {obs.get('instructions', '')}

TOPIC BEING ANALYZED: {obs['narrative_topic']}
LAST ACTION RESULT: {obs.get('last_action_result', 'None')}

ACCOUNTS IN BATCH:
{accounts_text}

STRATEGY:
- If you don't have enough info on an account, use action_type: "investigate".
- Available tools: "view_posts", "view_metadata", "view_network".
- Once you have analyzed sufficient accounts to find the network, use action_type: "submit".

Respond ONLY with a JSON object in one of these formats:

To Investigate:
{{
  "action_type": "investigate",
  "target_account_id": "acc_001",
  "investigation_tool": "view_posts",
  "reasoning": "Need to see post content to check for messaging similarities."
}}

To Submit Final Decisions:
{{
  "action_type": "submit",
  "account_decisions": {{
    "acc_001": "flag_cib",
    "acc_002": "clear",
    ...
  }},
  "network_description": "<describe the CIB network>",
  "reasoning": "Finalizing investigation after finding evidence of coordinated messaging."
}}"""


def build_appeal_prompt(obs: dict) -> str:
    return f"""You are an appeals reviewer at a social media platform.

TASK: appeal_review
INSTRUCTIONS: {obs.get('instructions', '')}

APPEAL ID: {obs['appeal_id']}

ORIGINAL POST: {obs['original_post_content']}
ORIGINAL DECISION: {obs['original_decision']}
POLICY CITED: {obs.get('original_policy_cited', 'None')}

USER'S APPEAL:
{obs['appeal_argument']}

{f"NEW EVIDENCE PROVIDED:{chr(10)}{obs['new_evidence']}" if obs.get('new_evidence') else "No new evidence provided."}

USER HISTORY:
- Account age: {obs['user_history']['account_age_days']} days
- Prior violations: {obs['user_history']['previous_violations']}
- Verified: {obs['user_history']['is_verified']}

RELEVANT POLICIES:
{chr(10).join(obs.get('policy_sections', [])[:4])}

Respond ONLY with a JSON object in this exact format:
{{
  "appeal_id": "{obs['appeal_id']}",
  "decision": "<uphold|overturn|modify_restrict|modify_age_gate>",
  "reasoning": "<clear explanation of your decision>",
  "policy_cited": "<policy_id or null>"
}}"""


def call_llm(prompt: str, task_name: str) -> dict:
    """Call the LLM and parse the JSON response."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a Trust & Safety AI agent. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=512,
            )
            content = response.choices[0].message.content.strip()
            # Strip markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            if attempt == max_retries - 1:
                print(f"[WARN] JSON parse failed after {max_retries} attempts: {e}", file=sys.stderr)
                return {}
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[WARN] LLM call failed: {e}", file=sys.stderr)
                return {}
            time.sleep(1)
    return {}


# ---------------------------------------------------------------------------
# Task runners
# ---------------------------------------------------------------------------

def run_task(env: TrustGuardEnv, task_name: str) -> float:
    """Run a full episode for one task. Returns final score."""
    t0 = time.time()
    log_start(task_name, MODEL_NAME)

    obs = env.reset(task_name)
    done = False
    step_num = 0
    scores = []

    while not done:
        step_num += 1

        # Build prompt based on task type
        if task_name == "coordinated_inauthentic_behavior":
            prompt = build_cib_prompt(obs)
        elif task_name == "appeal_review":
            prompt = build_appeal_prompt(obs)
        else:
            prompt = build_moderation_prompt(obs)

        action = call_llm(prompt, task_name)

        if not action:
            # Fallback to safe default if LLM fails
            if task_name == "coordinated_inauthentic_behavior":
                action = {
                    "action_type": "submit",
                    "account_decisions": {acc["account_id"]: "clear" for acc in obs["accounts"]},
                    "reasoning": "fallback"
                }
            elif task_name == "appeal_review":
                action = {"appeal_id": obs.get("appeal_id", ""), "decision": "uphold", "reasoning": "fallback"}
            else:
                action = {"post_id": obs.get("post_id", ""), "decision": "approve", "policy_violated": None, "severity": "none", "reasoning": "fallback"}

        obs, reward, done, info = env.step(action)

        # Extract item_id for logging
        item_id = (
            reward.get("post_id")
            or reward.get("appeal_id")
            or (f"investigate_{action.get('target_account_id')}" if action.get("action_type") == "investigate" else "cib_submit")
        )
        decision = action.get("decision") or action.get("action_type") or str(action.get("account_decisions", "batch"))
        step_score = reward.get("score", 0.0)
        cumulative = reward.get("cumulative_score", 0.0)
        scores.append(step_score)

        log_step(
            step=step_num,
            item_id=item_id,
            decision=str(decision)[:50],
            score=step_score,
            cumulative=cumulative,
            info={"feedback": reward.get("feedback", "")[:100]},
        )

    final_score = sum(scores) / len(scores) if scores else 0.0
    elapsed = time.time() - t0
    log_end(task_name, final_score, step_num, elapsed)
    return final_score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(json.dumps({
        "event": "INFO",
        "message": "TrustGuard-Env baseline inference starting",
        "model": MODEL_NAME,
        "api_base": API_BASE_URL,
        "tasks": ["spam_detection", "policy_enforcement", "coordinated_inauthentic_behavior", "appeal_review"],
    }), flush=True)

    env = TrustGuardEnv()
    all_scores = {}
    total_start = time.time()

    for task in ["spam_detection", "policy_enforcement", "coordinated_inauthentic_behavior", "appeal_review"]:
        score = run_task(env, task)
        all_scores[task] = round(score, 4)

    overall = sum(all_scores.values()) / len(all_scores)
    total_elapsed = time.time() - total_start

    print(json.dumps({
        "event": "SUMMARY",
        "scores": all_scores,
        "overall_score": round(overall, 4),
        "total_elapsed_seconds": round(total_elapsed, 2),
        "model": MODEL_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), flush=True)

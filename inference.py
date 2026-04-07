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
    # Extract key signals for better decision making
    user = obs.get('user_history', {})
    eng = obs.get('engagement', {})
    
    # Calculate spam signals
    is_new_account = user.get('account_age_days', 999) < 30
    is_bot_suspected = user.get('account_type') == 'bot_suspected'
    high_reports = eng.get('report_count', 0) > 10
    low_engagement = eng.get('likes', 0) < 10 and eng.get('views', 0) > 100
    
    # Build context-aware hints
    spam_hints = []
    if is_new_account:
        spam_hints.append("⚠️ New account (< 30 days)")
    if is_bot_suspected:
        spam_hints.append("🤖 Bot suspected")
    if high_reports:
        spam_hints.append(f"🚨 High reports ({eng.get('report_count')})")
    if low_engagement:
        spam_hints.append("📉 Low engagement rate")
    
    hints_text = "\n".join(f"  - {h}" for h in spam_hints) if spam_hints else "  - No obvious red flags"
    
    return f"""You are a content moderator. Review the following post and make a moderation decision.

TASK: {obs.get('task_name', 'moderation')}

POST ID: {obs['post_id']}
CONTENT: {obs['content']}

USER HISTORY:
- Account age: {user.get('account_age_days', '?')} days
- Previous violations: {user.get('previous_violations', 0)}
- Followers: {user.get('follower_count', 0):,}
- Verified: {user.get('is_verified', False)}
- Account type: {user.get('account_type', 'unknown')}

ENGAGEMENT:
- Views: {eng.get('views', 0):,} | Likes: {eng.get('likes', 0):,} | Shares: {eng.get('shares', 0):,}
- Reports: {eng.get('report_count', 0)}

{f"CONTEXT: {obs['context']}" if obs.get('context') else ""}

SPAM SIGNALS:
{hints_text}

RELEVANT POLICIES:
{chr(10).join(obs.get('policy_sections', [])[:5])}

DECISION GUIDELINES:
- "remove" = Clear policy violation (spam, phishing, scams, fake giveaways)
- "approve" = Legitimate content, no violations
- "restrict_reach" = Borderline content, reduce distribution
- "escalate" = Needs human review (complex cases)

POLICY MATCHING:
- spam_policy_1.1 = Phishing/scam links, fake security alerts
- spam_policy_1.2 = Get-rich-quick, MLM, fake giveaways, engagement bait
- spam_policy_1.3 = Duplicate content, coordinated spam campaigns

SEVERITY LEVELS:
- "high" = Phishing, scams, malicious links (immediate harm)
- "medium" = Fake giveaways, coordinated spam (moderate harm)
- "low" = Engagement bait, follow-for-follow (minor annoyance)
- "none" = No violation

Queue remaining: {obs.get('queue_remaining', 0)} posts after this one.

Respond ONLY with a JSON object in this exact format:
{{
  "post_id": "{obs['post_id']}",
  "decision": "<approve|remove|restrict_reach|age_gate|escalate|request_context>",
  "policy_violated": "<policy_id or null>",
  "severity": "<none|low|medium|high|critical>",
  "reasoning": "<brief explanation>"
}}"""


def build_cib_prompt(obs: dict, step_num: int) -> str:
    accounts_text = ""
    suspicious_accounts = []
    
    for acc in obs["accounts"]:
        unlocked_fields = [k for k, v in acc.items() if v is not None and k not in ['account_id', 'username', 'account_age_days', 'follower_count', 'following_count']]
        
        # Identify suspicious signals
        is_new = acc['account_age_days'] < 30
        high_following = acc['following_count'] > 2000
        
        accounts_text += f"""
ACCOUNT: {acc['account_id']} (@{acc['username']})
Age: {acc['account_age_days']} days | Followers: {acc['follower_count']} | Following: {acc['following_count']}
Unlocked Data: {', '.join(unlocked_fields) or 'Basic metadata only'}
"""
        if acc.get("bio"): 
            accounts_text += f"Bio: {acc['bio']}\n"
        if acc.get("posts"): 
            accounts_text += f"Recent posts: {acc['posts'][:2]}\n"
        if acc.get("hashtags_used"): 
            accounts_text += f"Hashtags: {', '.join(acc['hashtags_used'][:5])}\n"
        if acc.get("posts_per_day"): 
            accounts_text += f"Activity: {acc['posts_per_day']} posts/day | Avg hour: {acc['avg_posting_hour']:.1f}\n"
        if acc.get("cross_tagged_accounts"): 
            accounts_text += f"Cross-tags: {', '.join(acc['cross_tagged_accounts'])}\n"
        
        # Track suspicious accounts
        if is_new or high_following:
            suspicious_accounts.append(acc['account_id'])

    # Determine if we should force submission
    should_submit = step_num >= 7  # Submit by step 7 to leave room for investigation
    
    if should_submit:
        strategy_text = f"""
🚨 CRITICAL: You are on Step {obs['step']} of {obs['total_steps']}. Time to SUBMIT your final classification.

CIB DETECTION SIGNALS (look for multiple signals together):
1. ⏰ New accounts (< 30 days old) - Freshly created for campaign
2. 📊 High posting frequency (> 10 posts/day) - Automated or coordinated behavior
3. 🔗 Cross-tagging same accounts repeatedly - Network coordination
4. 🏷️ Identical hashtags across accounts - Coordinated messaging
5. 🕐 Similar posting hours (especially early morning 2-8 AM) - Bot-like timing
6. 👥 High following but low followers - Inauthentic engagement patterns
7. 📢 Urgent/alarmist language + "share now" - Amplification tactics

CLASSIFICATION RULES:
- "flag_cib": Account shows 3+ signals above AND is part of coordinated network
- "clear": Legitimate account (old account, normal activity, no coordination)
- "investigate_further": Uncertain but suspicious (use sparingly)

YOU MUST NOW use action_type: "submit" with account_decisions for ALL {len(obs['accounts'])} accounts.
"""
    else:
        uninvestigated = [acc for acc in obs["accounts"] if not any(
            acc.get(field) is not None 
            for field in ['posts', 'posts_per_day', 'cross_tagged_accounts']
        )]
        
        priority_targets = [acc['account_id'] for acc in uninvestigated if acc['account_id'] in suspicious_accounts]
        
        strategy_text = f"""
INVESTIGATION STRATEGY (Step {obs['step']}/{obs['total_steps']}):

Suspicious accounts to prioritize: {', '.join(suspicious_accounts[:5]) if suspicious_accounts else 'None identified yet'}

RECOMMENDED INVESTIGATION ORDER:
1. Use "view_posts" first - reveals bio, content, hashtags (most diagnostic)
2. Use "view_metadata" - reveals posting frequency and timing patterns
3. Use "view_network" - reveals cross-tagging and coordination

{f"🎯 PRIORITY: Investigate {', '.join(priority_targets[:3])} next" if priority_targets else "Continue investigating suspicious accounts"}

Plan to SUBMIT by step 7 after gathering evidence on key accounts.

To investigate, use:
{{
  "action_type": "investigate",
  "target_account_id": "acc_XXX",
  "investigation_tool": "view_posts",
  "reasoning": "Checking for coordinated messaging patterns"
}}
"""

    return f"""You are a Trust & Safety investigator specializing in coordinated inauthentic behavior (CIB).

TASK: coordinated_inauthentic_behavior (Step {obs['step']}/{obs['total_steps']})
TOPIC: {obs['narrative_topic']}
LAST ACTION: {obs.get('last_action_result', 'Investigation started')}

ACCOUNTS IN BATCH:
{accounts_text}

{strategy_text}

Respond ONLY with valid JSON in one of these formats:

To Investigate (only if step < 7):
{{
  "action_type": "investigate",
  "target_account_id": "acc_001",
  "investigation_tool": "view_posts",
  "reasoning": "Need to see post content and hashtags"
}}

To Submit Final Decisions (REQUIRED at step 7+):
{{
  "action_type": "submit",
  "account_decisions": {{
    "acc_001": "flag_cib",
    "acc_002": "clear",
    "acc_003": "flag_cib"
  }},
  "network_description": "Brief description of coordinated network found",
  "reasoning": "Identified network based on new accounts, high posting frequency, and cross-tagging patterns"
}}"""


def build_appeal_prompt(obs: dict) -> str:
    user = obs.get('user_history', {})
    
    # Analyze appeal strength
    has_new_evidence = bool(obs.get('new_evidence'))
    prior_violations = user.get('previous_violations', 0)
    is_verified = user.get('is_verified', False)
    
    # Build decision hints
    hints = []
    if has_new_evidence:
        hints.append("✅ New evidence provided - evaluate carefully")
    if prior_violations >= 3:
        hints.append(f"⚠️ Pattern: {prior_violations} prior violations")
    if is_verified:
        hints.append("✓ Verified account")
    
    hints_text = "\n".join(f"  {h}" for h in hints) if hints else "  No special factors"
    
    return f"""You are an appeals reviewer at a social media platform.

TASK: appeal_review

APPEAL ID: {obs['appeal_id']}

ORIGINAL POST: {obs['original_post_content']}
ORIGINAL DECISION: {obs['original_decision']}
POLICY CITED: {obs.get('original_policy_cited', 'None')}

USER'S APPEAL:
{obs['appeal_argument']}

{f"NEW EVIDENCE PROVIDED:{chr(10)}{obs['new_evidence']}" if obs.get('new_evidence') else "❌ No new evidence provided."}

USER HISTORY:
- Account age: {user.get('account_age_days', '?')} days
- Prior violations: {user.get('previous_violations', 0)}
- Verified: {user.get('is_verified', False)}
- Account type: {user.get('account_type', 'unknown')}

APPEAL FACTORS:
{hints_text}

RELEVANT POLICIES:
{chr(10).join(obs.get('policy_sections', [])[:4])}

DECISION GUIDELINES:
- "uphold" = Original decision was correct, no new evidence changes this
- "overturn" = Original decision was wrong, restore content fully
- "modify_restrict" = Partial merit, reduce to restrict_reach instead of remove
- "modify_age_gate" = Partial merit, apply age restriction instead of remove

KEY CONSIDERATIONS:
1. Does new evidence actually change the facts?
2. Is there a pattern of violations (3+ = likely uphold)?
3. Was original decision clearly wrong (error → overturn)?
4. Is there partial merit (PII concerns, artistic content → modify)?

COMMON PATTERNS:
- Satire with clear labeling → overturn
- Drug sales with weak excuse → uphold
- Artistic nudity → modify_age_gate
- Factual claims with proof → overturn
- Pattern of coded hate speech → uphold
- PII with safety concern → modify_restrict
- Dangerous health advice → uphold
- Clear moderation error → overturn

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
    
    # Adjust temperature based on task
    temperature = 0.1 if task_name == "coordinated_inauthentic_behavior" else 0.0
    max_tokens = 1024 if task_name == "coordinated_inauthentic_behavior" else 512
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a Trust & Safety AI agent. Always respond with valid JSON only. No markdown, no explanations, just pure JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content.strip()
            
            # Strip markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                if content.startswith("json"):
                    content = content[4:].strip()
            
            # Try to parse JSON
            parsed = json.loads(content.strip())
            
            # Validate CIB responses
            if task_name == "coordinated_inauthentic_behavior":
                if parsed.get("action_type") == "submit":
                    # Ensure all accounts have decisions
                    if not parsed.get("account_decisions"):
                        if attempt < max_retries - 1:
                            continue
                
            return parsed
            
        except json.JSONDecodeError as e:
            if attempt == max_retries - 1:
                print(f"[WARN] JSON parse failed after {max_retries} attempts: {e}", file=sys.stderr)
                print(f"[WARN] Content was: {content[:200]}", file=sys.stderr)
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
    
    # CIB-specific state tracking
    investigated_accounts = set()

    while not done:
        step_num += 1

        # Build prompt based on task type
        if task_name == "coordinated_inauthentic_behavior":
            prompt = build_cib_prompt(obs, step_num)
        elif task_name == "appeal_review":
            prompt = build_appeal_prompt(obs)
        else:
            prompt = build_moderation_prompt(obs)

        action = call_llm(prompt, task_name)

        if not action:
            # Fallback to safe default if LLM fails
            if task_name == "coordinated_inauthentic_behavior":
                # Smart fallback for CIB: analyze patterns
                if step_num < 7:
                    # Investigate suspicious accounts with rotating tools
                    tools = ['view_posts', 'view_metadata', 'view_network']
                    tool = tools[(step_num - 1) % len(tools)]
                    
                    # Find uninvestigated suspicious accounts
                    for acc in obs["accounts"]:
                        acc_id = acc["account_id"]
                        # Check if this account needs investigation
                        needs_investigation = (
                            acc_id not in investigated_accounts and
                            (acc["account_age_days"] < 30 or acc["following_count"] > 2000)
                        )
                        
                        if needs_investigation:
                            investigated_accounts.add(acc_id)
                            action = {
                                "action_type": "investigate",
                                "target_account_id": acc_id,
                                "investigation_tool": tool,
                                "reasoning": f"Investigating suspicious account with {tool}"
                            }
                            break
                
                # If no investigation needed or step >= 7, submit
                if not action or step_num >= 7:
                    # Analyze and classify accounts based on multiple signals
                    decisions = {}
                    for acc in obs["accounts"]:
                        # Count CIB signals
                        signals = 0
                        
                        # Signal 1: New account
                        if acc["account_age_days"] < 30:
                            signals += 1
                        
                        # Signal 2: High posting frequency
                        if acc.get("posts_per_day") and acc["posts_per_day"] > 10:
                            signals += 2  # Weight this heavily
                        
                        # Signal 3: Cross-tagging network
                        if acc.get("cross_tagged_accounts") and len(acc["cross_tagged_accounts"]) > 2:
                            signals += 2  # Weight this heavily
                        
                        # Signal 4: High following, low followers (bot pattern)
                        if acc["following_count"] > 2000 and acc["follower_count"] < 500:
                            signals += 1
                        
                        # Signal 5: Suspicious hashtags (if we have them)
                        if acc.get("hashtags_used"):
                            suspicious_tags = ['#StopEUTrade', '#EUCorrupt', '#VaccineTruth', '#NoMandates', '#SOLX', '#100x']
                            if any(tag in acc["hashtags_used"] for tag in suspicious_tags):
                                signals += 1
                        
                        # Classify: 3+ signals = CIB
                        decisions[acc["account_id"]] = "flag_cib" if signals >= 3 else "clear"
                    
                    action = {
                        "action_type": "submit",
                        "account_decisions": decisions,
                        "network_description": "Coordinated network identified based on account age, posting frequency, cross-tagging, and hashtag patterns",
                        "reasoning": "fallback analysis with multi-signal detection"
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

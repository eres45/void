---
title: TrustGuard-Env
emoji: 🛡️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
short_description: Real-world Trust & Safety OpenEnv environment for training content moderation agents
---

# TrustGuard-Env 🛡️

**A real-world OpenEnv environment simulating Meta-scale Trust & Safety operations.**

AI agents act as content moderators — reviewing posts, enforcing platform policies, detecting coordinated disinformation networks, and handling user appeals. Mirrors the actual workflows used by social media Trust & Safety teams at scale.

---

## Why This Environment

Social media platforms moderate **billions of pieces of content daily**. This is one of the hardest, most consequential decision-making workflows in tech. TrustGuard-Env provides:

- A realistic simulation of content moderation pipelines
- Rich, non-sparse reward signals with genuine precision/recall tradeoffs
- Tasks that range from straightforward pattern recognition to complex network analysis
- A benchmark that genuinely challenges frontier models on the hard task

---

## Tasks

| Task | Difficulty | Steps | Description |
|------|-----------|-------|-------------|
| `spam_detection` | Easy | 15 | Identify spam vs. legitimate posts (phishing, scams, bots, duplicate content) |
| `policy_enforcement` | Medium | 12 | Enforce platform policies on nuanced content (hate speech, misinformation, PII, satire) |
| `coordinated_inauthentic_behavior` | Hard | 1 | Detect a coordinated disinformation network from behavioral signals across 10 accounts |
| `appeal_review` | Medium | 8 | Review user appeals against moderation decisions, weighing new evidence |

---

## Observation Space

All tasks return structured JSON observations. Fields vary by task:

### Post Moderation Tasks (spam_detection, policy_enforcement)
```json
{
  "task_name": "spam_detection",
  "step": 1,
  "post_id": "sp_001",
  "content": "Post text...",
  "user_history": {
    "account_age_days": 12,
    "previous_violations": 0,
    "follower_count": 47,
    "is_verified": false,
    "account_type": "personal"
  },
  "engagement": {
    "views": 320, "likes": 3, "shares": 1,
    "comments": 0, "report_count": 8
  },
  "context": "Additional context if available",
  "policy_sections": ["policy_id: policy text..."],
  "queue_remaining": 14,
  "instructions": "Task instructions..."
}
```

### CIB Task
```json
{
  "task_name": "coordinated_inauthentic_behavior",
  "accounts": [
    {
      "account_id": "acc_001",
      "username": "...",
      "bio": "...",
      "account_age_days": 2190,
      "follower_count": 34200,
      "following_count": 1240,
      "posts": ["post 1", "post 2", "..."],
      "hashtags_used": ["#tag1"],
      "avg_posting_hour": 14.2,
      "posts_per_day": 1.3,
      "cross_tagged_accounts": []
    }
  ],
  "narrative_topic": "Anti-EU trade policy",
  "time_window_hours": 48,
  "instructions": "..."
}
```

### Appeal Review Task
```json
{
  "task_name": "appeal_review",
  "appeal_id": "ap_001",
  "original_post_content": "...",
  "original_decision": "remove",
  "original_policy_cited": "misinformation_policy_4.1",
  "appeal_argument": "User's appeal...",
  "new_evidence": "Evidence provided (if any)",
  "user_history": {...},
  "policy_sections": [...],
  "queue_remaining": 7,
  "instructions": "..."
}
```

---

## Action Space

### Post Moderation (Tasks 1 & 2)
```json
{
  "post_id": "sp_001",
  "decision": "remove",
  "policy_violated": "spam_policy_1.2",
  "severity": "high",
  "reasoning": "Post contains get-rich-quick scheme language with suspicious link"
}
```

Valid decisions: `approve` | `remove` | `restrict_reach` | `age_gate` | `escalate` | `request_context`  
Valid severities: `none` | `low` | `medium` | `high` | `critical`

### CIB Task
```json
{
  "account_decisions": {
    "acc_001": "clear",
    "acc_003": "flag_cib",
    "acc_007": "flag_cib"
  },
  "network_description": "Accounts 003, 007, 009, 012, 015 show coordinated posting...",
  "reasoning": "These accounts share identical hashtags, cross-tag each other..."
}
```

Valid account decisions: `flag_cib` | `clear` | `investigate_further`

### Appeal Review (Task 4)
```json
{
  "appeal_id": "ap_001",
  "decision": "overturn",
  "reasoning": "New evidence shows account is a verified satire creator...",
  "policy_cited": "satire_exemption_3.4"
}
```

Valid decisions: `uphold` | `overturn` | `modify_restrict` | `modify_age_gate`

---

## Reward Function

All rewards are in the range [0.0, 1.0].

### Tasks 1 & 2 (per step)
```
reward = 0.50 × correctness
       + 0.25 × policy_accuracy
       + 0.15 × severity_accuracy
       - 0.05 × false_positive_penalty
       - 0.05 × false_negative_penalty
```

- **Partial credit** for adjacent decisions (e.g., `escalate` instead of `remove` = 0.6 credit)
- **False positives** (removing clean content) penalized less than **false negatives** (missing real harm)

### Task 3 CIB (single step)
```
score = F1(precision, recall) of CIB network detection
```
- `investigate_further` on true CIB accounts = 0.5 partial credit

### Task 4 Appeals (per step)
```
reward = correctness (with partial credit for adjacent decisions)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns 200 |
| `GET` | `/tasks` | List all tasks |
| `POST` | `/reset` | Start new episode `{"task_name": "spam_detection"}` |
| `POST` | `/step` | Submit action `{"action": {...}}` |
| `GET` | `/state` | Get current episode state |

---

## Setup & Running

### Local

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --host 0.0.0.0 --port 7860

# Run baseline inference
export HF_TOKEN=your_api_key
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
python inference.py
```

### Docker

```bash
docker build -t trustguard-env .
docker run -p 7860:7860 \
  -e HF_TOKEN=your_key \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o-mini \
  trustguard-env
```

### Hugging Face Spaces

The environment is deployed at: `[HF Space URL]`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | Yes | API key for LLM calls |
| `API_BASE_URL` | Yes | LLM API endpoint base URL |
| `MODEL_NAME` | Yes | Model identifier for inference |

---

## Inference Script Output Format

`inference.py` emits structured JSON to stdout:

```
{"event": "START", "task": "spam_detection", "model": "gpt-4o-mini", "timestamp": "..."}
{"event": "STEP", "step": 1, "item_id": "sp_001", "decision": "remove", "score": 1.0, "cumulative_score": 1.0}
{"event": "STEP", "step": 2, "item_id": "sp_002", "decision": "remove", "score": 0.85, "cumulative_score": 0.925}
...
{"event": "END", "task": "spam_detection", "total_score": 0.78, "steps": 15, "elapsed_seconds": 23.4}
{"event": "SUMMARY", "scores": {...}, "overall_score": 0.61}
```

---

## Baseline Scores (gpt-4o-mini)

| Task | Expected Score |
|------|---------------|
| spam_detection | ~0.72 |
| policy_enforcement | ~0.48 |
| coordinated_inauthentic_behavior | ~0.30 |
| appeal_review | ~0.55 |
| **Overall** | **~0.51** |

---

## Project Structure

```
trustguard-env/
├── env/
│   ├── __init__.py
│   ├── environment.py       # Main TrustGuardEnv class
│   ├── models.py            # Pydantic typed models
│   ├── reward.py            # Unified reward function
│   ├── tasks/               # 4 task implementations
│   ├── graders/             # 4 deterministic graders
│   └── data/                # Synthetic datasets + policy handbook
├── inference.py             # Baseline inference script (root, mandatory)
├── app.py                   # FastAPI server
├── openenv.yaml             # OpenEnv specification
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## License

MIT

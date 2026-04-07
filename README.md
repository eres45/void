---
title: TrustGuard-Env
emoji: 🛡️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
short_description: "OpenEnv Trust & Safety agent training environment"
---

<div align="center">

# 🛡️ TrustGuard-Env

### *An OpenEnv-Compliant Environment for Training AI Content Moderation Agents*

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-brightgreen?style=for-the-badge&logo=checkmarx)](https://openenv.dev)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](Dockerfile)

**Submitted to the Meta × Hugging Face Hackathon 2026**

[📖 Live Demo](#live-demo) • [🚀 Quick Start](#quick-start) • [📊 Benchmark Results](#benchmark-results) • [🔧 API Reference](#api-reference)

</div>

---

## 🎯 Overview

Social media platforms moderate **billions of pieces of content every day**. This is one of the most challenging, consequential decision-making workflows in technology — requiring agents to balance free speech, user safety, legal compliance, and platform health simultaneously.

**TrustGuard-Env** simulates the full Trust & Safety operations pipeline at Meta scale. AI agents act as content moderators, navigating real-world dilemmas:

> *"Is this dark humor or a genuine threat? Should we remove this or just restrict reach? Is this a coordinated disinformation campaign or just a coincidence?"*

This environment is designed for **RL agent training**, **LLM evaluation**, and **AI safety research**.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TrustGuard-Env System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌───────────────┐    OpenEnv API     ┌──────────────────────┐  │
│   │               │◄──────────────────►│                      │  │
│   │   AI Agent    │   JSON over HTTP   │   FastAPI Server     │  │
│   │               │                   │   (app.py)           │  │
│   └───────────────┘                   └──────────┬───────────┘  │
│                                                   │              │
│                                     ┌─────────────▼──────────┐  │
│                                     │   TrustGuardEnv         │  │
│                                     │   (environment.py)      │  │
│                                     └─────────────┬──────────┘  │
│                                                   │              │
│         ┌─────────────────────────────────────────┼─────────┐   │
│         │                   Tasks                 │         │   │
│         │  ┌──────────────┐   ┌───────────────┐  │         │   │
│         │  │ spam_detect  │   │ policy_enforce│  │         │   │
│         │  │  (Easy·15)   │   │  (Med·12)     │  │         │   │
│         │  └──────┬───────┘   └───────┬───────┘  │         │   │
│         │         │                   │           │         │   │
│         │  ┌──────▼───────┐   ┌───────▼───────┐  │         │   │
│         │  │  CIB Invest. │   │ appeal_review │  │         │   │
│         │  │  (Hard·10)   │   │  (Med·8)      │  │         │   │
│         │  └──────────────┘   └───────────────┘  │         │   │
│         └─────────────────────────────────────────┘         │   │
│                                                               │   │
│   ┌────────────────┐   ┌────────────────┐   ┌─────────────┐ │   │
│   │  Graders (×4)  │   │  Reward Shaper │   │  Data Layer │ │   │
│   │  F1 / Partial  │   │  Adjacency Map │   │  JSON Scen. │ │   │
│   └────────────────┘   └────────────────┘   └─────────────┘ │   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Task Suite

| Task | Difficulty | Steps | Action Space | Key Challenge |
|------|:----------:|:-----:|:------------:|:-------------|
| `spam_detection` | 🟢 Easy | 15 | 6 decisions | Pattern recognition under adversarial obfuscation |
| `policy_enforcement` | 🟡 Medium | 12 | 6 decisions + policy citation | Nuanced edge cases: satire, art, context |
| `coordinated_inauthentic_behavior` | 🔴 Hard | 10 | Investigate + Submit | Multi-step evidence gathering, network reasoning |
| `appeal_review` | 🟡 Medium | 8 | 4 decisions | Weighing new evidence against prior decisions |

### Difficulty Progression

```
DIFFICULTY
   Hard  ────────────────────────────────────────── CIB (10 steps)
         │                                          ↕
  Medium ─────────────────────── Policy (12 steps) ↕  Appeal (8 steps)
         │                                          ↕
   Easy  ──── Spam (15 steps)                       ↕
         │                                          ↕
STEPS:   0    5    10    15   ←→  REASONING DEPTH: Low ──── High
```

---

## 🛡️ The CIB Interactive Investigation (Key Novelty)

The **Hard** task implements a unique **Partially Observable Investigation Engine**. Instead of receiving all data upfront (a simple classification task), the agent must **actively discover evidence** using investigative tools.

```
Initial State (Agent sees):          After Investigation (Agent unlocks):
┌──────────────────────────┐         ┌──────────────────────────────────┐
│ acc_001 | @username      │         │ acc_001 | @username              │
│ Age: 7 days              │         │ Age: 7 days                      │
│ Followers: 23            │  ──►    │ Posts: ["Vaccine microchips...", │
│ Following: 8,500         │ tools   │         "The WHO is hiding..."]  │
│ [Bio: LOCKED 🔒]         │         │ Avg Post Hour: 3.2 AM            │
│ [Posts: LOCKED 🔒]       │         │ Cross-tags: acc_003, acc_007     │
│ [Network: LOCKED 🔒]     │         │ Posts/day: 47.3                  │
└──────────────────────────┘         └──────────────────────────────────┘
```

**Investigation Tools:**
```
view_posts     → Unlocks: Bio, recent post content, top hashtags
view_metadata  → Unlocks: Posting frequency, avg. hour, behavioral timing  
view_network   → Unlocks: Cross-tagged accounts, network mentions, hub analysis
```

**Why this matters:** Real Trust & Safety investigators don't see a dashboard with all data at once. They pivot from signal to signal. This mechanic creates genuine **agentic behavior**—agents must plan their investigation strategy, allocate their 10 steps wisely, and reason about what evidence is most diagnostic.

---

## 📊 Observation Space

All tasks return structured JSON conforming to typed Pydantic models.

### Post Moderation Tasks
```json
{
  "task_name": "spam_detection",
  "step": 1,
  "post_id": "sp_001",
  "content": "🚨 URGENT: Your account will be SUSPENDED unless you click here...",
  "user_history": {
    "account_age_days": 3,
    "previous_violations": 0,
    "follower_count": 8,
    "is_verified": false,
    "account_type": "personal"
  },
  "engagement": {
    "views": 45, "likes": 0, "shares": 2,
    "comments": 0, "report_count": 12
  },
  "context": "Link leads to credential harvesting site.",
  "policy_sections": ["spam_policy_1.1: ...", "phishing_policy_6.2: ..."],
  "queue_remaining": 14,
  "instructions": "Review and classify this post..."
}
```

### CIB Investigation Observation (after using view_posts)
```json
{
  "task_name": "coordinated_inauthentic_behavior",
  "step": 3,
  "total_steps": 10,
  "last_action_result": "Successfully used view_posts on acc_003.",
  "accounts": [
    {
      "account_id": "acc_003",
      "username": "truth_seeker_99",
      "account_age_days": 12,
      "follower_count": 23,
      "following_count": 8420,
      "bio": "Waking people up to what THEY don't want you to know [UNLOCKED]",
      "posts": ["Vaccine microchips are REAL...", "Follow @acc_007 for truth"],
      "hashtags_used": ["#WakeUp", "#TheyLie", "#ShareNow"]
    }
  ],
  "narrative_topic": "Anti-vaccine misinformation campaign",
  "time_window_hours": 72
}
```

---

## ⚡ Action Space

### Post Moderation (Tasks 1 & 2)
```json
{
  "post_id": "sp_001",
  "decision": "remove",
  "policy_violated": "phishing_policy_6.2",
  "severity": "high",
  "reasoning": "Classic credential-harvesting phishing link with urgency manipulation."
}
```

| Decision | Description |
|:--------:|:------------|
| `approve` | Content is fine — no action needed |
| `remove` | Clear policy violation — remove immediately |
| `restrict_reach` | Reduce algorithmic distribution without removal |
| `age_gate` | Restrict to 18+ audiences only |
| `escalate` | Forward to specialist human review team |
| `request_context` | Insufficient information — request more context |

### CIB Investigation Actions
```json
// INVESTIGATE (gather evidence)
{
  "action_type": "investigate",
  "target_account_id": "acc_003",
  "investigation_tool": "view_network",
  "reasoning": "acc_003 appears in multiple cross-tags. Need to map the hub structure."
}

// SUBMIT (final classification)
{
  "action_type": "submit",
  "account_decisions": {
    "acc_001": "flag_cib",
    "acc_003": "flag_cib",
    "acc_007": "flag_cib",
    "acc_002": "clear",
    "acc_005": "clear"
  },
  "network_description": "5-node coordinated network amplifying anti-vaccine narratives...",
  "reasoning": "Accounts share synchronized posting hours (2-4 AM), identical hashtags..."
}
```

---

## 🏆 Reward Function

All rewards in range **[0.0, 1.0]** with rich non-sparse signals.

### Post Moderation (Tasks 1 & 2)

```
score = 0.50 × decision_correctness
      + 0.25 × policy_accuracy  
      + 0.15 × severity_accuracy
      − 0.05 × false_positive_penalty
      − 0.05 × false_negative_penalty
```

**Partial Credit via Decision Adjacency:**

```
                    DECISION ADJACENCY MAP
                    
   approve ──0.4── age_gate ──0.6── restrict_reach ──0.4── remove ──0.6── escalate
      │                                                         │
      └────────── 0.3 ─────── request_context                  │
                                                                │
                        False Positive Cost: 0.4               │
                        False Negative Cost: 0.5 ──────────────┘
                        
Example: Predicted "escalate" when answer is "remove" → 0.6 × 0.5 = 0.30 score
         Predicted "approve" when answer is "remove"  → 0.0 − 0.5 = 0.0 score
```

**Why This Matters for RL Training:** Most content moderation benchmarks give binary 0/1 rewards. TrustGuard-Env provides **gradient information** in the action space — agents learn that "escalate" is closer to "remove" than "approve" is, enabling faster policy gradient convergence.

### CIB Network Detection (Task 3)

```
score = F1(precision, recall) of CIB account classification

where:
  precision = True Positives / (True Positives + False Positives)
  recall    = True Positives / (True Positives + False Negatives)
  F1        = 2 × (precision × recall) / (precision + recall)

Partial credit: "investigate_further" on true CIB accounts = 0.5 × full credit
```

### Appeal Review (Task 4)

```
Appeal Decision Adjacency:

  uphold ──0.4── modify_restrict ──0.6── modify_age_gate ──0.4── overturn
     └──────────────── 0.4 ──────────── modify_age_gate

Binary errors (uphold ↔ overturn) = 0.0 — no partial credit for reversing decisions
```

---

## 📈 Benchmark Results

Scores generated using `inference.py` against **Meta Llama 3.1 8B Instruct** via OpenAI-compatible API:

### Per-Task Performance

```
TASK                           | SCORE | VISUALIZATION
───────────────────────────────┼───────┼──────────────────────────────────
spam_detection (Easy)          │ 0.853 │ ████████████████████████████░░░░  85%
policy_enforcement (Medium)    │ 0.686 │ ████████████████████████░░░░░░░░  69%
coordinated_inauthentic (Hard) │ 1.000 │ █████████████████████████████████ 100%
appeal_review (Medium)         │ 0.600 │ ████████████████████░░░░░░░░░░░░  60%
───────────────────────────────┼───────┼──────────────────────────────────
OVERALL                        │ 0.785 │ ██████████████████████████░░░░░░  78%
```

### Why CIB = 100%?

The 8B model perfectly identified the coordinated network. This demonstrates that the environment's **partial observability mechanics** (the investigative action space) create the right level of challenge — the task is **solvable** but requires deliberate multi-step strategy.

### Policy Enforcement Breakdown

The policy enforcement task shows the most interesting failure modes:

```
pe_001 (Hate Speech):        1.00  ██████████  Clear violation
pe_002 (Satire):             1.00  ██████████  Correctly approved
pe_003 (PII Exposure):       0.55  █████░░░░░  Right action, wrong policy cited
pe_004 (Health Misinfo):     0.55  █████░░░░░  Right action, wrong policy cited
pe_006 (Illegal Goods):      0.65  ██████░░░░  Right action, wrong policy category
pe_007 (Self-Harm):          0.37  ████░░░░░░  "remove" when "escalate" was needed
pe_010 (Classical Art):      0.28  ███░░░░░░░  "approve" when "age_gate" needed
pe_011 (Election Misinfo):   0.28  ███░░░░░░░  "remove" when "restrict_reach" needed
```

These failures represent genuine Trust & Safety edge cases where even expert humans disagree — exactly what makes this environment valuable for training.

---

## 🔧 API Reference

The environment exposes a RESTful API compliant with the OpenEnv specification:

| Method | Path | Request Body | Response |
|:------:|:-----|:-------------|:---------|
| `GET` | `/health` | — | `{"status": "ok", "service": "trustguard-env", "version": "1.0.0"}` |
| `GET` | `/tasks` | — | Array of task metadata |
| `POST` | `/reset` | `{"task_name": "spam_detection"}` | Initial observation |
| `POST` | `/step` | `{"action": {...}}` | Observation, reward, done, info |
| `GET` | `/state` | — | Current episode state |
| `GET` | `/demo` | — | Interactive Gradio UI |

### Example Session

```bash
# 1. Start an episode
curl -X POST http://localhost:7860/reset \
  -H 'Content-Type: application/json' \
  -d '{"task_name": "spam_detection"}'

# 2. Submit a moderation decision
curl -X POST http://localhost:7860/step \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {
      "post_id": "sp_001",
      "decision": "remove",
      "policy_violated": "spam_policy_1.2",
      "severity": "high",
      "reasoning": "Classic phishing attempt"
    }
  }'

# 3. Check episode state
curl http://localhost:7860/state
```

---

## 🚀 Quick Start

### Local Development

```bash
# Clone and install
git clone https://huggingface.co/spaces/eressss/trustguard-env
cd trustguard-env
pip install -r requirements.txt

# Run the environment server
uvicorn app:app --host 0.0.0.0 --port 7860 --reload

# Run baseline inference (requires OpenAI-compatible API)
export API_BASE_URL=https://api.openai.com/v1
export HF_TOKEN=sk-your-api-key
export MODEL_NAME=gpt-4o-mini
python inference.py
```

### Docker Deployment

```bash
docker build -t trustguard-env .
docker run -p 7860:7860 \
  -e HF_TOKEN=sk-your-api-key \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o-mini \
  trustguard-env
```

### Integration (Python Client)

```python
import httpx

BASE = "http://localhost:7860"

# Reset environment
obs = httpx.post(f"{BASE}/reset", json={"task_name": "spam_detection"}).json()

while True:
    # Your agent logic here
    action = your_agent.act(obs["observation"])
    
    result = httpx.post(f"{BASE}/step", json={"action": action}).json()
    obs = result
    
    print(f"Reward: {result['reward']['score']:.3f}")
    
    if result["done"]:
        break
```

---

## 📁 Project Structure

```
trustguard-env/
├── env/
│   ├── __init__.py
│   ├── environment.py       ← Core TrustGuardEnv class (reset/step/state)
│   ├── models.py            ← Pydantic typed models (Observations, Actions, Rewards)
│   ├── reward.py            ← Unified reward shaping (adjacency, F1, penalties)
│   ├── tasks/
│   │   ├── spam_task.py         ← 15-step spam detection
│   │   ├── policy_task.py       ← 12-step policy enforcement
│   │   ├── cib_task.py          ← 10-step interactive investigation ⭐
│   │   └── appeal_task.py       ← 8-step appeal review
│   ├── graders/
│   │   ├── spam_grader.py       ← Moderation reward computation
│   │   ├── policy_grader.py     ← Policy citation accuracy grading
│   │   ├── cib_grader.py        ← F1-based network detection grading
│   │   └── appeal_grader.py     ← Appeal decision grading
│   └── data/
│       ├── spam_posts.json      ← 15 high-quality spam scenarios
│       ├── policy_posts.json    ← 12 nuanced policy edge cases
│       ├── cib_scenarios.json   ← 3 CIB investigation scenarios
│       ├── appeals.json         ← 8 moderation appeal cases
│       └── policies.json        ← Platform policy handbook
├── app.py                   ← FastAPI server + Gradio mount
├── demo.py                  ← Interactive Gradio demo UI
├── inference.py             ← Baseline agent + structured logging
├── test_smoke.py            ← Smoke test suite
├── openenv.yaml             ← OpenEnv specification
├── Dockerfile               ← Production Docker image
├── requirements.txt
└── README.md
```

---

## 🌍 Real-World Scenario Depth

Each task features carefully crafted scenarios that mirror genuine Trust & Safety dilemmas:

**Spam Detection** — Covers: promotional keyword spam, phishing, credential harvesting, duplicate content bombing, bot behavior, account compromise signals

**Policy Enforcement** — Covers: hate speech (explicit vs. coded language), health misinformation (real harm potential), PII exposure, controlled substance solicitation, election integrity, self-harm signals, satirical content, classical art vs. nudity

**CIB Investigation** — Covers: anti-EU political disinformation, vaccine misinformation amplification, cryptocurrency pump-and-dump promotion across 3 distinct scenarios (prevents memorization)

**Appeal Review** — Covers: satire misidentification, artistic content appeals, prior violation history weighing, new evidence review, age-gating vs. removal tradeoffs

---

## 🔬 OpenEnv Specification

```yaml
# openenv.yaml (excerpt)
name: trustguard-env
version: "1.0.0"
domain: trust_and_safety
tasks:
  - name: spam_detection
    difficulty: easy
    max_steps: 15
  - name: policy_enforcement
    difficulty: medium
    max_steps: 12
  - name: coordinated_inauthentic_behavior
    difficulty: hard
    max_steps: 10   # Stateful multi-step investigation
  - name: appeal_review
    difficulty: medium
    max_steps: 8
reward_range: [0.0, 1.0]
action_space: structured_json
observation_space: structured_json
environment:
  stateful: true
  deterministic: true
  seed: 42
```

---

## ⚙️ Environment Variables

| Variable | Required | Description | Example |
|----------|:--------:|:------------|:--------|
| `API_BASE_URL` | ✅ | OpenAI-compatible LLM API endpoint | `https://api.openai.com/v1` |
| `HF_TOKEN` | ✅ | Your API key for the LLM provider | `sk-...` |
| `MODEL_NAME` | ✅ | Model identifier | `gpt-4o-mini` |

> **Note:** Any OpenAI-compatible API provider works (OpenAI, Together.ai, Frenix, Anyscale, etc.)

---

## 📝 Baseline Inference Log Format

`inference.py` emits structured JSONL to stdout (required format):

```jsonl
{"event": "INFO", "message": "TrustGuard-Env baseline inference starting", "model": "llama-3.1-8b-instruct", "tasks": ["spam_detection", ...]}
{"event": "START", "task": "spam_detection", "model": "llama-3.1-8b-instruct", "timestamp": "2026-04-07T05:07:26Z"}
{"event": "STEP", "step": 1, "item_id": "sp_001", "decision": "remove", "score": 0.9, "cumulative_score": 0.9, "info": {"feedback": "..."}}
{"event": "STEP", "step": 2, "item_id": "sp_002", "decision": "approve", "score": 0.775, "cumulative_score": 0.837, "info": {...}}
...
{"event": "END", "task": "spam_detection", "total_score": 0.853, "steps": 15, "elapsed_seconds": 147.2}
{"event": "SUMMARY", "scores": {"spam_detection": 0.853, "policy_enforcement": 0.686, "coordinated_inauthentic_behavior": 1.000, "appeal_review": 0.600}, "overall_score": 0.785, "model": "llama-3.1-8b-instruct"}
```

---

## Live Demo

Access the interactive Gradio demo at: **https://eressss-trustguard-env.hf.space**

Space URL: https://huggingface.co/spaces/eressss/trustguard-env

The demo allows you to manually:
- Browse moderation queues and submit decisions
- Investigate CIB accounts using the investigation tools
- See per-step rewards and feedback in real time

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the [Meta × Hugging Face Hackathon 2026](https://huggingface.co/)**

*Advancing AI agent research in Trust & Safety*

🛡️ **TrustGuard-Env** | OpenEnv Compliant | MIT License

</div>

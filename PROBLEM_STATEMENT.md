# 🏆 Meta Hackathon — Round 1 Problem Statement

## The Task

Build a **complete, real-world OpenEnv environment** that an AI agent can learn from through the standard `step()` / `reset()` / `state()` API.

---

## ✅ Key Requirements at a Glance

- Must simulate a **real-world task** (not games or toys)
- Implement **full OpenEnv spec**: typed models, `step()` / `reset()` / `state()`, `openenv.yaml`
- **Minimum 3 tasks** with agent graders (easy → medium → hard, scores 0.0–1.0)
- **Meaningful reward function** with partial progress signals
- **Baseline inference script** with reproducible scores
- **Deploy to Hugging Face Spaces** + working Dockerfile
- **README** with environment description, action/observation spaces, setup instructions

---

## 📋 Functional Requirements

### 1. Real-World Task Simulation
The environment must simulate a task humans actually do. **Not games, not toys.**
Examples: email triage, code review, data cleaning, scheduling, customer support, content moderation.

### 2. OpenEnv Spec Compliance
- Implement the full OpenEnv interface: typed `Observation`, `Action`, and `Reward` Pydantic models
- `step(action)` → returns observation, reward, done, info
- `reset()` → returns initial observation
- `state()` → returns current state
- `openenv.yaml` with metadata
- Tested via `openenv validate`

### 3. Minimum 3 Tasks with Agent Graders
- Each task defines a concrete objective an agent must accomplish
- Programmatic grader that scores performance (0.0–1.0)
- Tasks must range: **easy → medium → hard**
- Graders must have **clear, deterministic** success/failure criteria

### 4. Meaningful Reward Function
- Provides signal over the **full trajectory** (not just binary end-of-episode)
- Rewards **partial progress** toward task completion
- Penalizes clearly undesirable behavior (e.g. infinite loops, destructive actions)

### 5. Baseline Inference Script
- Uses the **OpenAI API client** to run a model against the environment
- Reads API credentials from environment variables (`OPENAI_API_KEY`)
- Produces a **reproducible baseline score** on all 3 tasks

---

## 📊 Scoring Breakdown

| Parameter | Weight | Description |
|-----------|--------|-------------|
| Real-world utility | **30%** | Does the environment model a genuine task? Would someone actually use this to train or evaluate agents? |
| Task & grader quality | **25%** | Are tasks well-defined with clear objectives? Do graders accurately and fairly measure success? Meaningful difficulty progression? |
| Environment design | **20%** | Clean state management, sensible action/observation spaces, good reward shaping, proper episode boundaries. |
| Code quality & spec compliance | **15%** | Follows OpenEnv spec, clean project structure, typed models, documented, tested, Dockerfile works. |
| Creativity & novelty | **10%** | Novel problem domain, interesting mechanics, clever reward design, original approach. |

### Real-World Utility (30%)
- **0–5**: Toy/artificial problem with no practical application
- **6–15**: Valid domain but shallow modeling of the real task
- **16–25**: Good domain modeling, would be useful for agent evaluation
- **26–30**: Excellent — fills a real gap, immediate value for the RL/agent community

### Task & Grader Quality (25%)
- 3+ tasks with difficulty range?
- Graders produce scores between 0.0–1.0?
- Graders deterministic and reproducible?
- Hard task genuinely challenges frontier models?

### Environment Design (20%)
- `reset()` produces clean state?
- Action/observation types well-designed and documented?
- Reward function provides useful varying signal (not just sparse)?
- Episode boundaries sensible?

### Code Quality & Spec Compliance (15%)
- `openenv validate` passes?
- `docker build && docker run` works?
- HF Space deploys and responds?
- Baseline script runs and reproduces scores?

### Creativity & Novelty (10%)
- Domain we haven't seen in OpenEnv before?
- Reward design has interesting properties?
- Clever mechanics that make the environment engaging?

---

## 🔄 Evaluation Phases

### Phase 1: Automated Validation (Pass/Fail Gate)
HF Space deploys, OpenEnv spec compliance, Dockerfile builds, baseline reproduces, 3+ tasks with graders.

### Phase 2: Agentic Evaluation (Scored)
Baseline agent re-run, standard Open LLM agent (e.g. Nemotron 3 Super) run against all environments, score variance check.

### Phase 3: Human Review
Top submissions reviewed by Meta and Hugging Face engineers for real-world utility, creativity, and exploit checks.

---

## 🚫 Disqualification Criteria

- Environment does not deploy or respond
- Plagiarized or trivially modified existing environments
- Graders that always return the same score
- No baseline inference script

---

## ✅ Pre-Submission Checklist (ALL must pass or disqualified)

| Check | Requirement |
|-------|-------------|
| HF Space deploys | Automated ping to the Space URL — must return 200 and respond to `reset()` |
| OpenEnv spec compliance | Validate `openenv.yaml`, typed models, `step()`/`reset()`/`state()` endpoints |
| Dockerfile builds | Automated docker build on the submitted repo |
| Baseline reproduces | Run the submitted inference script — must complete without error and produce scores |
| 3+ tasks with graders | Enumerate tasks, run each grader, verify scores in 0.0–1.0 range |

---

## ⚙️ Mandatory Additional Instructions

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | The API endpoint for the LLM |
| `MODEL_NAME` | The model identifier to use for inference |
| `HF_TOKEN` | Your Hugging Face / API key |

### Inference Script Rules
- Must be named **`inference.py`** and placed in the **root directory**
- Must use **OpenAI Client** for all LLM calls using the above variables
- Must emit **structured stdout logs** strictly following the `[START]`, `[STEP]`, and `[END]` format defined in the sample `inference.py`
- **Any deviation in field names, ordering, or formatting = incorrect evaluation scoring**

---

## 🖥️ Infra Restrictions

- Runtime of inference script: **< 20 minutes**
- Must run on: **vCPU=2, Memory=8GB**

---

## 🔍 Validator

Run the pre-submission validation script before submitting.

---

*Last updated: 2026-04-02*

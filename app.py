"""
TrustGuard-Env — FastAPI Server for Hugging Face Spaces
Exposes OpenEnv-compliant HTTP endpoints + mounts the Gradio interactive demo.

Endpoints:
  GET  /health   — health check
  GET  /tasks    — list all tasks
  POST /reset    — start new episode
  POST /step     — submit action
  GET  /state    — get current state
  GET  /         — root info
  GET  /demo     — interactive Gradio demo (mounted)
"""

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Any

from env.environment import TrustGuardEnv, VALID_TASKS
from demo import build_demo
import threading

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TrustGuard-Env",
    description=(
        "A real-world OpenEnv environment simulating Meta-scale Trust & Safety operations. "
        "AI agents act as content moderators across 4 tasks of increasing difficulty. "
        "Built for the Meta x HuggingFace Hackathon 2026."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance (stateful per-session)
env = TrustGuardEnv()
env_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Request / Response models (inline for simplicity)
# ---------------------------------------------------------------------------
from pydantic import BaseModel


class ResetRequest(BaseModel):
    task_name: str = "spam_detection"


class StepRequest(BaseModel):
    action: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Health check — required for HF Spaces automated ping."""
    return {"status": "ok", "service": "trustguard-env", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    """List all available tasks with metadata."""
    return {
        "tasks": [
            {
                "name": "spam_detection",
                "difficulty": "easy",
                "max_steps": 15,
                "description": "Detect spam vs. legitimate posts",
            },
            {
                "name": "policy_enforcement",
                "difficulty": "medium",
                "max_steps": 12,
                "description": "Enforce policies on contextually nuanced content",
            },
            {
                "name": "coordinated_inauthentic_behavior",
                "difficulty": "hard",
                "max_steps": 1,
                "description": "Detect coordinated disinformation networks",
            },
            {
                "name": "appeal_review",
                "difficulty": "medium",
                "max_steps": 8,
                "description": "Review user appeals against moderation decisions",
            },
        ]
    }


@app.post("/reset")
def reset(request: ResetRequest = None):
    """
    Reset the environment and start a new episode.
    Body: {"task_name": "spam_detection"} (Optional)
    """
    task_name = request.task_name if request else "spam_detection"

    if task_name not in VALID_TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task '{task_name}'. Valid tasks: {VALID_TASKS}",
        )
    with env_lock:
        obs = env.reset(task_name)
    return {
        "observation": obs,
        "task_name": task_name,
        "total_steps": _get_total_steps(task_name),
        "message": f"Episode started for task: {task_name}",
    }


@app.post("/step")
def step(request: StepRequest):
    """
    Submit an action and advance the environment one step.
    Body: {"action": {...}}
    Returns: {observation, reward, done, info}
    """
    if not request.action:
        raise HTTPException(status_code=400, detail="Action cannot be empty.")
    try:
        with env_lock:
            obs, reward, done, info = env.step(request.action)
        return {
            "observation": obs,
            "reward": reward,
            "done": done,
            "info": info,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step error: {str(e)}")


@app.get("/state")
def state():
    """Return the current environment state."""
    with env_lock:
        return env.state()


@app.get("/")
def root():
    """Redirect root to the interactive Gradio demo."""
    return RedirectResponse(url="/demo")


@app.get("/api")
def api_info():
    """API metadata endpoint."""
    return {
        "name": "TrustGuard-Env",
        "description": "Real-world Trust & Safety OpenEnv environment",
        "version": "1.0.0",
        "tasks": VALID_TASKS,
        "docs": "/docs",
        "demo": "/demo",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Mount Gradio demo at /demo
# ---------------------------------------------------------------------------
gradio_demo = build_demo()
app = gr.mount_gradio_app(app, gradio_demo, path="/demo")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


def _get_total_steps(task_name: str) -> int:
    return {
        "spam_detection": 15,
        "policy_enforcement": 12,
        "coordinated_inauthentic_behavior": 1,
        "appeal_review": 8,
    }.get(task_name, 0)

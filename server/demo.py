"""
TrustGuard-Env — Interactive Gradio Demo
Provides a visual interface for judges and users to experience the environment.
Mounted at /demo on the FastAPI server.
"""

import json
import gradio as gr
from env.environment import TrustGuardEnv, VALID_TASKS

# Global env instance for the demo
_demo_env = TrustGuardEnv()
_demo_obs = {}
_demo_done = False

DECISION_CHOICES = {
    "spam_detection": ["approve", "remove", "restrict_reach", "age_gate", "escalate", "request_context"],
    "policy_enforcement": ["approve", "remove", "restrict_reach", "age_gate", "escalate", "request_context"],
    "coordinated_inauthentic_behavior": ["flag_cib", "clear", "investigate_further"],
    "appeal_review": ["uphold", "overturn", "modify_restrict", "modify_age_gate"],
}

SEVERITY_CHOICES = ["none", "low", "medium", "high", "critical"]

TASK_DESCRIPTIONS = {
    "spam_detection": "🟢 **Easy** — Review 15 posts and identify spam vs. legitimate content",
    "policy_enforcement": "🟡 **Medium** — Enforce policies on 12 contextually nuanced posts (hate speech, PII, misinformation)",
    "coordinated_inauthentic_behavior": "🔴 **Hard** — Investigate 10 accounts over 10 steps and detect a coordinated disinformation network",
    "appeal_review": "🟡 **Medium** — Review 8 user appeals against moderation decisions",
}


def format_observation(obs: dict, task: str) -> str:
    """Format observation as readable markdown."""
    if not obs:
        return "No observation yet. Select a task and click **Start Episode**."

    if task == "coordinated_inauthentic_behavior":
        lines = [
            f"## 🔍 CIB Investigation",
            f"**Narrative Topic:** {obs.get('narrative_topic', 'N/A')}",
            f"**Time Window:** {obs.get('time_window_hours', 'N/A')} hours",
            f"**Accounts to Analyze:** {len(obs.get('accounts', []))}",
            "",
            "---",
        ]
        for acc in obs.get("accounts", []):
            lines += [
                f"### 👤 `{acc['account_id']}` — @{acc['username']}",
                f"*{acc['bio']}*",
                f"📅 Age: **{acc['account_age_days']} days** | 👥 Followers: **{acc['follower_count']}** | Following: **{acc['following_count']}**",
                f"📊 Posts/day: **{acc['posts_per_day']}** | Avg hour: **{acc['avg_posting_hour']:.1f}**",
                f"🏷️ Hashtags: `{'`, `'.join(acc.get('hashtags_used', [])[:5])}`",
                f"🔗 Cross-tags: {', '.join(acc.get('cross_tagged_accounts', [])) or 'None'}",
                "**Recent Posts:**",
            ]
            for p in acc.get("posts", [])[:2]:
                lines.append(f"> {p[:150]}{'...' if len(p) > 150 else ''}")
            lines.append("")
        return "\n".join(lines)

    elif task == "appeal_review":
        return f"""## ⚖️ Appeal Review — `{obs.get('appeal_id', '')}`
**Step {obs.get('step', '?')}** | {obs.get('queue_remaining', 0)} remaining

---
### Original Post
> {obs.get('original_post_content', '')}

**Original Decision:** `{obs.get('original_decision', '')}` | **Policy:** `{obs.get('original_policy_cited', 'N/A')}`

---
### User's Appeal
{obs.get('appeal_argument', '')}

{"**New Evidence:** " + obs.get('new_evidence', '') if obs.get('new_evidence') else '*(No new evidence provided)*'}

---
### Account History
- Account age: **{obs.get('user_history', {}).get('account_age_days', '?')} days**
- Prior violations: **{obs.get('user_history', {}).get('previous_violations', '?')}**
- Verified: **{obs.get('user_history', {}).get('is_verified', False)}**
"""
    else:
        user = obs.get("user_history", {})
        eng = obs.get("engagement", {})
        return f"""## 📋 Post Moderation — Step {obs.get('step', '?')}
**Task:** `{obs.get('task_name', '')}` | **Queue remaining:** {obs.get('queue_remaining', 0)}

---
### Post `{obs.get('post_id', '')}`
> {obs.get('content', '')}

---
### Account Info
- 📅 Age: **{user.get('account_age_days', '?')} days** | Type: **{user.get('account_type', '?')}**
- ⚠️ Prior violations: **{user.get('previous_violations', 0)}** | ✅ Verified: **{user.get('is_verified', False)}**
- 👥 Followers: **{user.get('follower_count', 0):,}**

### Engagement
👁️ {eng.get('views', 0):,} views | ❤️ {eng.get('likes', 0):,} likes | 🚨 {eng.get('report_count', 0)} reports

{"**Context:** " + obs.get('context', '') if obs.get('context') else ''}

---
### Relevant Policies
{chr(10).join("- " + p[:120] for p in obs.get('policy_sections', [])[:3])}
"""


def start_episode(task_name: str):
    global _demo_env, _demo_obs, _demo_done
    _demo_obs = _demo_env.reset(task_name)
    _demo_done = False
    state = _demo_env.state()
    obs_text = format_observation(_demo_obs, task_name)
    status = f"✅ Episode started | Steps: 0/{state['total_steps']} | Score: 0.00"
    return obs_text, status, "", gr.update(visible=True)


def submit_action(task_name: str, action_type: str, target_id: str, tool: str, decision: str, policy: str, severity: str, reasoning: str):
    global _demo_env, _demo_obs, _demo_done

    if _demo_done:
        return format_observation(_demo_obs, task_name), "⚠️ Episode complete. Start a new episode.", "Episode already done."

    if task_name == "coordinated_inauthentic_behavior":
        if action_type == "investigate":
            action = {
                "action_type": "investigate",
                "target_account_id": target_id,
                "investigation_tool": tool,
                "reasoning": reasoning or "Investigating account " + target_id
            }
        else:
            # For CIB submission, apply the selected decision to all accounts for Demo simplicity
            accounts = _demo_obs.get("accounts", [])
            account_decisions = {acc["account_id"]: decision for acc in accounts}
            action = {
                "action_type": "submit",
                "account_decisions": account_decisions, 
                "reasoning": reasoning or "Final submission"
            }
    elif task_name == "appeal_review":
        action = {
            "appeal_id": _demo_obs.get("appeal_id", ""),
            "decision": decision,
            "reasoning": reasoning or "Demo reasoning",
            "policy_cited": policy or None,
        }
    else:
        action = {
            "post_id": _demo_obs.get("post_id", ""),
            "decision": decision,
            "policy_violated": policy or None,
            "severity": severity,
            "reasoning": reasoning or "Demo reasoning",
        }

    try:
        new_obs, reward, done, info = _demo_env.step(action)
        _demo_done = done
        state = _demo_env.state()
        score = reward.get("score", reward.get("f1_score", 0))
        cumulative = reward.get("cumulative_score", state["cumulative_score"])

        reward_text = f"""### 🏆 Reward
**Step Score:** `{score:.3f}` | **Cumulative:** `{cumulative:.3f}`
**Feedback:** {reward.get('feedback', '')}
{"**Correctness:** " + str(reward.get('correctness', '')) if 'correctness' in reward else ''}
{"**Policy Accuracy:** " + str(reward.get('policy_accuracy', '')) if 'policy_accuracy' in reward else ''}
{"**Severity Accuracy:** " + str(reward.get('severity_accuracy', '')) if 'severity_accuracy' in reward else ''}
{"**F1 Score:** " + str(reward.get('f1_score', '')) if 'f1_score' in reward else ''}
"""
        if done:
            status = f"🎯 Episode complete | Score: {cumulative:.3f} | {'✅ Well done!' if cumulative >= 0.7 else '📈 Room to improve'}"
            _demo_obs = {}
            new_obs_text = "Episode complete! Start a new episode to play again."
        else:
            _demo_obs = new_obs
            status = f"▶️ Step {state['current_step']}/{state['total_steps']} | Cumulative: {cumulative:.3f}"
            new_obs_text = format_observation(new_obs, task_name)

        return new_obs_text, status, reward_text
    except Exception as e:
        return format_observation(_demo_obs, task_name), f"❌ Error: {str(e)}", ""


def build_demo():
    with gr.Blocks(
        title="TrustGuard-Env Demo",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
        css="""
        .header { text-align: center; padding: 20px; }
        .status-bar { font-weight: bold; padding: 8px; border-radius: 4px; }
        """,
    ) as demo:
        gr.Markdown("""
# 🛡️ TrustGuard-Env — Interactive Demo
**Real-world Trust & Safety environment for AI agent training**

*Simulates the content moderation workflows at Meta scale — 4 tasks, 4 difficulty levels.*
""")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Task Selection")
                task_dropdown = gr.Dropdown(
                    choices=VALID_TASKS,
                    value="spam_detection",
                    label="Select Task",
                    info="Choose a moderation task to run",
                )
                task_desc = gr.Markdown(TASK_DESCRIPTIONS["spam_detection"])
                start_btn = gr.Button("🚀 Start Episode", variant="primary", size="lg")
                status_bar = gr.Markdown("*Select a task and start an episode*")

            with gr.Column(scale=2):
                obs_display = gr.Markdown("*Observation will appear here*", label="Current Observation")

        with gr.Row(visible=False) as action_row:
            with gr.Column():
                gr.Markdown("### 🎯 Take Action")
                
                # CIB Specific Controls
                with gr.Column(visible=False) as cib_controls:
                    with gr.Row():
                        action_type_radio = gr.Radio(
                            choices=["investigate", "submit"],
                            label="Action Type",
                            value="investigate"
                        )
                        target_acc_dropdown = gr.Dropdown(
                            choices=[], 
                            label="Target Account"
                        )
                    tool_radio = gr.Radio(
                        choices=["view_posts", "view_network", "view_metadata"],
                        label="Investigative Tool",
                        value="view_posts",
                        visible=True
                    )

                # Standard Moderation Controls
                with gr.Row() as mod_controls:
                    decision_radio = gr.Radio(
                        choices=DECISION_CHOICES["spam_detection"],
                        label="Decision",
                        value="approve",
                    )
                    severity_radio = gr.Radio(
                        choices=SEVERITY_CHOICES,
                        label="Severity",
                        value="none",
                    )
                
                policy_input = gr.Textbox(
                    label="Policy ID (if applicable)",
                    placeholder="e.g. spam_policy_1.2",
                )
                reasoning_input = gr.Textbox(
                    label="Reasoning / Investigative Log",
                    placeholder="Explain your action...",
                    lines=2,
                )
                submit_btn = gr.Button("✅ Perform Action", variant="primary")
                reward_display = gr.Markdown("")

        def update_task_desc(task):
            is_cib = (task == "coordinated_inauthentic_behavior")
            decisions = DECISION_CHOICES.get(task, DECISION_CHOICES["spam_detection"])
            return (
                TASK_DESCRIPTIONS.get(task, ""),
                gr.update(choices=decisions, value=decisions[0]),
                gr.update(visible=is_cib),
                gr.update(visible=not is_cib),
            )

        task_dropdown.change(
            update_task_desc,
            inputs=[task_dropdown],
            outputs=[task_desc, decision_radio, cib_controls, mod_controls],
        )

        def toggle_cib_action(action_type):
            return gr.update(visible=(action_type == "investigate"))

        action_type_radio.change(
            toggle_cib_action,
            inputs=[action_type_radio],
            outputs=[tool_radio]
        )

        def start_episode_with_targets(task_name: str):
            obs_text, status, reward, action_visible = start_episode(task_name)
            targets = []
            if task_name == "coordinated_inauthentic_behavior" and _demo_obs:
                targets = [a["account_id"] for a in _demo_obs.get("accounts", [])]
            return obs_text, status, reward, action_visible, gr.update(choices=targets, value=targets[0] if targets else None)

        start_btn.click(
            start_episode_with_targets,
            inputs=[task_dropdown],
            outputs=[obs_display, status_bar, reward_display, action_row, target_acc_dropdown],
        )

        submit_btn.click(
            submit_action,
            inputs=[
                task_dropdown, 
                action_type_radio, 
                target_acc_dropdown, 
                tool_radio, 
                decision_radio, 
                policy_input, 
                severity_radio, 
                reasoning_input
            ],
            outputs=[obs_display, status_bar, reward_display],
        )

        gr.Markdown("""
---
### 📚 Task Reference

| Task | Steps | Key Actions |
|------|-------|-------------|
| `spam_detection` | 15 | approve, remove |
| `policy_enforcement` | 12 | Full 6-action space + policy citation |
| `coordinated_inauthentic_behavior` | 10 | Investigate with tools, then submit: flag_cib, clear |
| `appeal_review` | 8 | uphold, overturn, modify_restrict, modify_age_gate |

**Reward Range:** 0.0 – 1.0 per step | **Partial credit** for adjacent decisions
""")

    return demo

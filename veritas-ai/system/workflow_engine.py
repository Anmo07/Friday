"""
Friday System — Advanced Automation Workflows (Phase 44)
=========================================================
Multi-step workflow engine that chains system actions into
named routines triggered by a single voice command.

Example:
  "Prepare my coding environment"
  → Opens IDE → Starts Docker → Loads project → Runs dev server

Workflows are defined declaratively and executed sequentially
with error handling and rollback support.
"""

import time
import logging
from typing import List, Optional
from system.control_engine import execute_action
from system.security_layer import validate_command

logger = logging.getLogger("friday.automation")


class WorkflowStep:
    """A single atomic step in a workflow."""
    def __init__(self, description: str, action: str, kwargs: dict,
                 delay_after: float = 1.0, critical: bool = True):
        self.description = description
        self.action = action
        self.kwargs = kwargs
        self.delay_after = delay_after
        self.critical = critical  # If True, workflow halts on failure


class Workflow:
    """A named sequence of WorkflowSteps."""
    def __init__(self, name: str, trigger_phrases: List[str], steps: List[WorkflowStep]):
        self.name = name
        self.trigger_phrases = [p.lower() for p in trigger_phrases]
        self.steps = steps

    def matches(self, text: str) -> bool:
        clean = text.lower().strip()
        return any(phrase in clean for phrase in self.trigger_phrases)


class WorkflowEngine:
    """Manages and executes multi-step workflows."""

    def __init__(self):
        self._workflows: List[Workflow] = []
        self._register_defaults()

    def _register_defaults(self):
        """Pre-built workflows for common developer routines."""

        self._workflows.append(Workflow(
            name="Prepare Coding Environment",
            trigger_phrases=["prepare my coding", "setup dev", "start coding", "dev environment"],
            steps=[
                WorkflowStep("Opening VS Code", "open_app", {"app_name": "Visual Studio Code"}),
                WorkflowStep("Starting Docker Desktop", "open_app", {"app_name": "Docker"}),
                WorkflowStep("Waiting for Docker to initialize", "shell", {"command": "sleep 3"}, delay_after=3.0),
                WorkflowStep("Starting development server", "shell", {
                    "command": "cd ~/Downloads/Developer/Friday/veritas-ai/frontend && npm run dev"
                }, critical=False),
                WorkflowStep("Opening project in browser", "open_url", {"url": "http://localhost:3000"}),
            ]
        ))

        self._workflows.append(Workflow(
            name="Morning Briefing",
            trigger_phrases=["morning briefing", "good morning", "start my day"],
            steps=[
                WorkflowStep("Opening Mail", "open_app", {"app_name": "Mail"}),
                WorkflowStep("Opening Calendar", "open_app", {"app_name": "Calendar"}),
                WorkflowStep("Opening Slack", "open_app", {"app_name": "Slack"}, critical=False),
                WorkflowStep("Setting volume to comfortable level", "set_volume", {"level": 40}),
                WorkflowStep("Checking the news", "open_url", {"url": "https://news.google.com"}),
            ]
        ))

        self._workflows.append(Workflow(
            name="End of Day",
            trigger_phrases=["end my day", "wind down", "done for today", "shutdown routine"],
            steps=[
                WorkflowStep("Saving all work", "shell", {"command": "echo 'Save reminder'"}, critical=False),
                WorkflowStep("Closing VS Code", "close_app", {"app_name": "Visual Studio Code"}, critical=False),
                WorkflowStep("Closing Docker", "close_app", {"app_name": "Docker"}, critical=False),
                WorkflowStep("Closing browser", "close_app", {"app_name": "Google Chrome"}, critical=False),
                WorkflowStep("Setting volume to zero", "set_volume", {"level": 0}),
            ]
        ))

        self._workflows.append(Workflow(
            name="Deploy Veritas AI",
            trigger_phrases=["deploy veritas", "deploy the system", "start deployment"],
            steps=[
                WorkflowStep("Building Docker images", "shell", {
                    "command": "cd ~/Downloads/Developer/Friday/veritas-ai && docker compose build --parallel"
                }, delay_after=2.0),
                WorkflowStep("Starting containers", "shell", {
                    "command": "cd ~/Downloads/Developer/Friday/veritas-ai && docker compose up -d"
                }),
                WorkflowStep("Verifying backend health", "shell", {
                    "command": "curl -s http://localhost:8000/api/v1/health"
                }, delay_after=3.0, critical=False),
                WorkflowStep("Opening dashboard", "open_url", {"url": "http://localhost:3000"}),
            ]
        ))

    def register_workflow(self, workflow: Workflow):
        """Add a custom workflow."""
        self._workflows.append(workflow)
        logger.info(f"Registered workflow: {workflow.name}")

    def find_workflow(self, text: str) -> Optional[Workflow]:
        """Match user text to a workflow."""
        for wf in self._workflows:
            if wf.matches(text):
                return wf
        return None

    def execute_workflow(self, workflow: Workflow, on_step: Optional[callable] = None) -> dict:
        """
        Execute all steps in a workflow sequentially.
        Returns a summary of execution results.
        """
        logger.info(f"🚀 Starting workflow: [{workflow.name}]")
        results = []
        failed = False

        for i, step in enumerate(workflow.steps):
            if failed:
                results.append({
                    "step": i + 1,
                    "description": step.description,
                    "status": "skipped",
                })
                continue

            logger.info(f"  Step {i+1}/{len(workflow.steps)}: {step.description}")

            if on_step:
                on_step(i + 1, len(workflow.steps), step.description)

            # Security check for shell commands
            if step.action == "shell":
                cmd = step.kwargs.get("command", "")
                validation = validate_command(cmd)
                if not validation.get("allowed", False):
                    results.append({
                        "step": i + 1,
                        "description": step.description,
                        "status": "blocked",
                        "reason": validation.get("reason", "Security policy"),
                    })
                    if step.critical:
                        failed = True
                    continue

            result = execute_action(step.action, **step.kwargs)
            status = result.get("status", "error") if isinstance(result, dict) else "success"

            results.append({
                "step": i + 1,
                "description": step.description,
                "status": status,
            })

            if status == "error" and step.critical:
                logger.error(f"  Critical step failed. Halting workflow.")
                failed = True
                continue

            if step.delay_after > 0:
                time.sleep(step.delay_after)

        overall = "completed" if not failed else "partial_failure"
        logger.info(f"Workflow [{workflow.name}] finished: {overall}")

        return {
            "workflow": workflow.name,
            "status": overall,
            "steps": results,
        }


# Global instance
workflow_engine = WorkflowEngine()

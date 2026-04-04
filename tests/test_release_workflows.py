"""Release-workflow checks for the governed CI and publish contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class ReleaseWorkflowTest(unittest.TestCase):
    """Verify the repo-owned build and publish workflow contract."""

    def _load_workflow(self, relative_path: str) -> dict[str, object]:
        """Load one workflow file without GitHub-key coercion."""

        repo_root = Path(__file__).resolve().parents[1]
        payload = yaml.load(
            (repo_root / relative_path).read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        self.assertIsInstance(payload, dict)
        return payload

    def test_ci_workflow_build_job_waits_for_governance(self) -> None:
        """Assert the generated CI workflow builds only after governance."""

        workflow = self._load_workflow(".github/workflows/ci.yml")
        jobs = workflow.get("jobs")
        self.assertIsInstance(jobs, dict)

        build_job = jobs.get("build")
        self.assertIsInstance(build_job, dict)
        self.assertEqual("governance", build_job.get("needs"))

        steps = build_job.get("steps")
        self.assertIsInstance(steps, list)
        step_names = [
            str(step.get("name") or "").strip()
            for step in steps
            if isinstance(step, dict)
        ]
        self.assertIn("Build distributions", step_names)
        self.assertIn("Validate distributions", step_names)
        self.assertIn("Generate build provenance", step_names)
        self.assertIn("Upload distributions", step_names)
        self.assertIn("Upload build provenance", step_names)

    def test_publish_workflow_uses_validated_ci_artifacts(self) -> None:
        """Assert manual publish downloads validated CI artifacts only."""

        workflow = self._load_workflow(".github/workflows/publish.yml")
        triggers = workflow.get("on")
        self.assertIsInstance(triggers, dict)

        dispatch = triggers.get("workflow_dispatch")
        self.assertIsInstance(dispatch, dict)
        inputs = dispatch.get("inputs")
        self.assertIsInstance(inputs, dict)

        ci_run_id = inputs.get("ci_run_id")
        self.assertIsInstance(ci_run_id, dict)
        self.assertEqual("true", ci_run_id.get("required"))

        jobs = workflow.get("jobs")
        self.assertIsInstance(jobs, dict)
        publish_job = jobs.get("publish")
        self.assertIsInstance(publish_job, dict)

        environment = publish_job.get("environment")
        self.assertIsInstance(environment, dict)
        self.assertEqual("pypi", environment.get("name"))
        self.assertEqual(
            "https://pypi.org/p/webcam-micro", environment.get("url")
        )

        steps = publish_job.get("steps")
        self.assertIsInstance(steps, list)
        step_names = [
            str(step.get("name") or "").strip()
            for step in steps
            if isinstance(step, dict)
        ]
        self.assertIn("Validate selected CI run", step_names)
        self.assertIn("Download validated distributions", step_names)
        self.assertIn("Download build provenance", step_names)
        self.assertIn("Verify downloaded provenance", step_names)
        self.assertIn("Publish to PyPI with trusted publishing", step_names)

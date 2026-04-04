"""Bootstrap checks for the freshly deployed repository."""

import unittest
from pathlib import Path


class BootstrapFilesTest(unittest.TestCase):
    """Verify core governed files exist after initial deployment."""

    def test_deploy_materializes_expected_files(self) -> None:
        """Assert the initial deploy wrote the expected core artifacts."""
        repo_root = Path(__file__).resolve().parents[1]
        expected_paths = (
            "AGENTS.md",
            "README.md",
            "CHANGELOG.md",
            ".pre-commit-config.yaml",
            ".github/workflows/ci.yml",
            ".github/workflows/publish.yml",
        )

        missing_paths = [
            relative_path
            for relative_path in expected_paths
            if not (repo_root / relative_path).exists()
        ]

        self.assertEqual(
            [],
            missing_paths,
            msg="Initial deployment should materialize the governed files.",
        )


if __name__ == "__main__":
    unittest.main()

"""Detect suspicious constructs via shared translator LanguageUnit."""

from __future__ import annotations

from typing import List

from devcovenant.core.policy_contract import (
    CheckContext,
    PolicyCheck,
    Violation,
)
from devcovenant.core.selectors import SelectorSet


class SecurityScannerCheck(PolicyCheck):
    """Flag known insecure constructs that breach compliance guidelines."""

    policy_id = "security-scanner"
    version = "1.2.0"
    DEFAULT_SUFFIXES = [
        ".py",
        ".pyi",
        ".pyw",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".cs",
    ]

    def check(self, context: CheckContext) -> List[Violation]:
        """Search repository modules through translator LanguageUnits."""
        violations: List[Violation] = []
        files = context.all_files or context.changed_files or []
        selector = SelectorSet.from_policy(
            self, defaults={"include_suffixes": self.DEFAULT_SUFFIXES}
        )
        runtime = context.translator_runtime
        if runtime is None:
            return violations

        for path in files:
            if not path.is_file() or not selector.matches(
                path, context.repo_root
            ):
                continue
            resolution = runtime.resolve(
                path=path,
                policy_id=self.policy_id,
                context=context,
            )
            if not resolution.is_resolved:
                if any(
                    "ambiguous" in violation.message.lower()
                    for violation in resolution.violations
                ):
                    violations.extend(resolution.violations)
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                violations.append(
                    Violation(
                        policy_id=self.policy_id,
                        severity="error",
                        file_path=path,
                        message=(
                            "Unable to read file as UTF-8 while scanning "
                            f"security constructs: {exc}"
                        ),
                    )
                )
                continue
            unit = runtime.translate(
                resolution,
                path=path,
                source=source,
                context=context,
            )
            if unit is None:
                continue
            for fact in unit.risk_facts:
                violations.append(
                    Violation(
                        policy_id=self.policy_id,
                        severity=fact.severity,
                        file_path=path,
                        line_number=fact.line_number,
                        message=(
                            "Insecure construct detected: " f"{fact.message}"
                        ),
                    )
                )

        return violations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.runtime_benchmark_evidence import (
    _action_has_artifact_lineage,
    _all_restored,
    _case_path,
    _float_policy_forbidden_changes,
    _human_status_output,
    _lineage_has_action,
    _load_json,
    format_report_lines,
    run_checks,
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).with_name("runtime_benchmark_evidence.py")
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


class RuntimeBenchmarkEvidenceOutputTest(unittest.TestCase):
    def test_case_path_preserves_absolute_paths_and_roots_relatives(self):
        with TemporaryDirectory() as tmpdir:
            benchmark_root = Path(tmpdir)
            absolute = benchmark_root / "absolute-case"

            self.assertEqual(_case_path(benchmark_root, str(absolute)), absolute)
            self.assertEqual(_case_path(benchmark_root, "AAAI/example"), benchmark_root / "AAAI/example")

    def test_all_restored_requires_nonempty_successful_restores(self):
        self.assertTrue(
            _all_restored(
                {
                    "restored_files": [
                        {"path": "main.tex", "restored": True},
                        {"path": "fig.tex", "restored": True},
                    ]
                }
            )
        )
        self.assertFalse(_all_restored({"restored_files": []}))
        self.assertFalse(
            _all_restored(
                {
                    "restored_files": [
                        {"path": "main.tex", "restored": True},
                        {"path": "fig.tex", "restored": False},
                    ]
                }
            )
        )

    def test_float_policy_forbidden_changes_flags_conservative_policy_violations(self):
        report = {
            "fix_report": {
                "changes": [
                    {"action": "insert \\FloatBarrier before section"},
                    {"action": "add placeins package"},
                ]
            },
            "space_report": {
                "changes": [
                    {"action": "tighten spacing", "after": "\u5168\u5c40\u57fa\u7ebf adjusted"},
                ]
            },
            "overflow_report": {
                "changes": [
                    {"action": "change float", "before": "[t]", "after": "from [t] to [ht]"},
                ]
            },
            "global_report": {
                "changes": [
                    {"action": "benign caption spacing"},
                    "malformed change is ignored",
                ]
            },
        }

        forbidden = _float_policy_forbidden_changes(report)

        self.assertEqual(len(forbidden), 4)
        self.assertTrue(any("\\FloatBarrier" in item for item in forbidden))
        self.assertTrue(any("placeins" in item for item in forbidden))
        self.assertTrue(any("\u5168\u5c40\u57fa\u7ebf" in item for item in forbidden))
        self.assertTrue(any("from [t] to [ht]" in item for item in forbidden))

    def test_action_has_artifact_lineage_requires_input_and_output_dicts(self):
        self.assertTrue(
            _action_has_artifact_lineage(
                {
                    "input_artifacts": {"main_tex": "main.tex"},
                    "output_artifacts": {"repair_plan": "data/repair_plan.json"},
                }
            )
        )
        self.assertFalse(_action_has_artifact_lineage({"input_artifacts": {}, "output_artifacts": []}))
        self.assertFalse(_action_has_artifact_lineage({"input_artifacts": {}}))

    def test_lineage_has_action_ignores_malformed_rounds(self):
        lineage = [
            "not a round",
            {"actions": ["compile"]},
            {"actions": {"repair_plan_executor": {"output_artifacts": {}}}},
        ]

        self.assertTrue(_lineage_has_action(lineage, "repair_plan_executor"))
        self.assertFalse(_lineage_has_action(lineage, "source_mutation_integrity"))
        self.assertFalse(_lineage_has_action({"actions": {}}, "repair_plan_executor"))

    def test_default_output_keeps_failures_and_hides_passes(self):
        report = {
            "passed": 1,
            "total": 3,
            "checks": [
                {"name": "passing check", "passed": True, "detail": "ok"},
                {"name": "first failing check", "passed": False, "detail": "missing artifact"},
                {"name": "second failing check", "passed": False, "detail": "stale artifact"},
            ],
        }

        lines = format_report_lines(report)

        self.assertEqual(lines[0], "runtime benchmark evidence: 1/3 checks passed")
        self.assertNotIn("[PASS] passing check - ok", lines)
        self.assertIn("[FAIL] first failing check - missing artifact", lines)
        self.assertIn("[FAIL] second failing check - stale artifact", lines)

    def test_verbose_output_includes_passes(self):
        report = {
            "passed": 1,
            "total": 2,
            "checks": [
                {"name": "passing check", "passed": True, "detail": "ok"},
                {"name": "failing check", "passed": False, "detail": "missing artifact"},
            ],
        }

        lines = format_report_lines(report, verbose=True)

        self.assertEqual(
            lines,
            [
                "runtime benchmark evidence: 1/2 checks passed",
                "[PASS] passing check - ok",
                "[FAIL] failing check - missing artifact",
            ],
        )

    def test_output_formatter_tolerates_missing_checks(self):
        report = {
            "passed": 0,
            "total": 0,
        }

        self.assertEqual(
            format_report_lines(report),
            ["runtime benchmark evidence: 0/0 checks passed"],
        )

    def test_output_formatter_tolerates_malformed_checks(self):
        report = {
            "passed": 0,
            "total": 3,
            "checks": [
                {"passed": False, "detail": "missing name"},
                {"name": "missing detail", "passed": False},
                "not a check dict",
            ],
        }

        self.assertEqual(
            format_report_lines(report),
            [
                "runtime benchmark evidence: 0/3 checks passed",
                "[FAIL] unnamed check - missing name",
                "[FAIL] missing detail - ",
                "[FAIL] malformed check - not a check dict",
            ],
        )

    def test_human_status_output_returns_stdout_on_success(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            (root / "data" / "state.json").write_text("{}", encoding="utf-8")
            completed = CompletedProcess(args=["node"], returncode=0, stdout="Status: ok\n", stderr="")

            with patch("scripts.runtime_benchmark_evidence.subprocess.run", return_value=completed):
                self.assertEqual(_human_status_output(root, "data/run_result.json"), "Status: ok\n")

    def test_human_status_output_returns_none_on_nonzero_exit(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            (root / "data" / "state.json").write_text("{}", encoding="utf-8")
            completed = CompletedProcess(args=["node"], returncode=1, stdout="", stderr="failed")

            with patch("scripts.runtime_benchmark_evidence.subprocess.run", return_value=completed):
                self.assertIsNone(_human_status_output(root, "data/run_result.json"))

    def test_human_status_output_returns_none_on_subprocess_timeout(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            (root / "data" / "state.json").write_text("{}", encoding="utf-8")

            with patch(
                "scripts.runtime_benchmark_evidence.subprocess.run",
                side_effect=TimeoutExpired(cmd=["node"], timeout=30),
            ):
                self.assertIsNone(_human_status_output(root, "data/run_result.json"))

    def test_human_status_output_skips_subprocess_without_state(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with patch("scripts.runtime_benchmark_evidence.subprocess.run") as run:
                self.assertIsNone(_human_status_output(root, "data/run_result.json"))

            run.assert_not_called()

    def test_load_json_returns_none_for_invalid_or_non_dict_json(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            invalid_json = root / "invalid.json"
            list_json = root / "list.json"
            invalid_json.write_text("{", encoding="utf-8")
            list_json.write_text("[]", encoding="utf-8")

            self.assertIsNone(_load_json(invalid_json))
            self.assertIsNone(_load_json(list_json))

    def test_load_json_returns_none_for_invalid_utf8(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid_utf8.json"
            path.write_bytes(b"\xff")

            self.assertIsNone(_load_json(path))

    def test_run_checks_short_circuits_when_benchmark_root_is_missing(self):
        with TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"

            report = run_checks(missing_root)

            self.assertEqual(report["total"], 1)
            self.assertEqual(report["passed"], 0)
            self.assertEqual(report["failed"], 1)
            self.assertEqual(report["checks"][0]["name"], "benchmark root exists")

    def test_cli_json_reports_missing_root_and_nonzero_exit(self):
        with TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"

            result = _run_cli(
                "--benchmark-root",
                str(missing_root),
                "--json",
            )

            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["benchmark_root"], str(missing_root.resolve()))
            self.assertEqual(report["total"], 1)
            self.assertEqual(report["failed"], 1)
            self.assertEqual(report["checks"][0]["name"], "benchmark root exists")
            self.assertEqual(result.stderr, "")

    def test_cli_text_reports_missing_root_and_nonzero_exit(self):
        with TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "missing"

            result = _run_cli(
                "--benchmark-root",
                str(missing_root),
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("runtime benchmark evidence: 0/1 checks passed", result.stdout)
            self.assertIn("[FAIL] benchmark root exists", result.stdout)
            self.assertIn(str(missing_root.resolve()), result.stdout)
            self.assertNotIn("[PASS]", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_cli_verbose_reports_passes_and_failures_for_empty_root(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            result = _run_cli(
                "--benchmark-root",
                str(root),
                "--verbose",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("runtime benchmark evidence:", result.stdout)
            self.assertIn(f"[PASS] benchmark root exists - {root}", result.stdout)
            self.assertIn("[FAIL] AAAI: canonical run result exists", result.stdout)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()

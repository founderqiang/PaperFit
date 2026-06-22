#!/usr/bin/env python3
"""Verify PaperFit typed-runtime benchmark evidence files.

This is an evidence checker, not a benchmark executor. It validates that the
controlled-copy protocol has already produced the expected runtime artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


BENCHMARK_CASES = [
    {
        "family": "AAAI",
        "canonical": "AAAI/arXiv-2305.09480v5",
        "copy": "AAAI/arXiv-2305.09480v5_runtime_copy_20260620",
    },
    {
        "family": "CVPR/ICCV",
        "canonical": "CVPRICCV/arXiv-2303.05725v4",
        "copy": "CVPRICCV/arXiv-2303.05725v4_runtime_copy_20260620",
    },
    {
        "family": "ECCV",
        "canonical": "ECCV/arXiv-2403.09394v1",
        "copy": "ECCV/arXiv-2403.09394v1_runtime_copy_20260621",
    },
    {
        "family": "ICLR",
        "canonical": "ICLR/arXiv-2209.12643v4",
        "copy": "ICLR/arXiv-2209.12643v4_runtime_copy_20260621",
    },
    {
        "family": "ACM MM",
        "canonical": "ACMmm/arXiv-2508.01427v2",
        "copy": "ACMmm/arXiv-2508.01427v2_runtime_copy_20260621",
    },
]

STALE_PLAN_CASE = {
    "family": "ACM MM",
    "copy": "ACMmm/arXiv-2508.01427v2_runtime_copy_20260621",
}

NONDRY_CASES = [
    {
        "family": "CVPR/ICCV",
        "copy": "CVPRICCV/arXiv-2303.05725v4_runtime_copy_20260620",
        "run_result": "data/run_result_full_vto_nondry_after_float_policy.json",
        "rollback_report": "data/rollback_report_after_float_policy.json",
        "status_view": "data/status_view_full_vto_nondry_after_float_policy.json",
    },
    {
        "family": "ECCV",
        "copy": "ECCV/arXiv-2403.09394v1_runtime_copy_20260621",
        "run_result": "data/run_result_full_vto_nondry_after_float_policy.json",
        "rollback_report": "data/rollback_report_after_float_policy.json",
        "status_view": "data/status_view_full_vto_nondry_after_float_policy.json",
    },
    {
        "family": "ICLR",
        "copy": "ICLR/arXiv-2209.12643v4_runtime_copy_20260621",
        "run_result": "data/run_result_full_vto_nondry_after_float_policy.json",
        "rollback_report": "data/rollback_report_after_float_policy.json",
        "status_view": "data/status_view_full_vto_nondry_after_float_policy.json",
    },
    {
        "family": "ACM MM",
        "copy": "ACMmm/arXiv-2508.01427v2_nondry_copy_20260621",
        "run_result": "data/run_result_full_vto_nondry_after_float_policy.json",
        "rollback_report": "data/rollback_report_after_float_policy.json",
        "status_view": "data/status_view_full_vto_nondry_after_float_policy.json",
    },
]

AGENT_V1_CASE = {
    "family": "AAAI Agent V1",
    "copy": "AAAI/arXiv-2305.09480v5_agent_v1_copy_20260621",
    "main_tex_sha256": "5771485ad6f5beae3c583c68d80b80dee0f50f4a005a845d0e8f355f0208e2ee",
}


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _case_path(benchmark_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else benchmark_root / path


def _freshness_status(run_result: Dict[str, Any]) -> Optional[str]:
    return ((run_result.get("artifact_manifest") or {}).get("freshness") or {}).get("status")


def _all_restored(report: Dict[str, Any]) -> bool:
    restored = report.get("restored_files") or []
    return bool(restored) and all(bool(item.get("restored")) for item in restored)


def _report_changes(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    for key in ("fix_report", "space_report", "overflow_report", "global_report"):
        section = report.get(key) or {}
        section_changes = section.get("changes") or []
        if isinstance(section_changes, list):
            changes.extend(item for item in section_changes if isinstance(item, dict))
    return changes


def _float_policy_forbidden_changes(report: Dict[str, Any]) -> List[str]:
    forbidden: List[str] = []
    for change in _report_changes(report):
        text = " ".join(
            str(change.get(key) or "")
            for key in ("action", "before", "after", "object", "defect_id")
        )
        if "placeins" in text or "\\FloatBarrier" in text:
            forbidden.append(text)
        if "全局基线" in text:
            forbidden.append(text)
        if "从 [t] 改为 [ht]" in text or "from [t] to [ht]" in text:
            forbidden.append(text)
    return forbidden


def _check(condition: bool, name: str, detail: str) -> Check:
    return Check(name=name, passed=condition, detail=detail)


def _action_has_artifact_lineage(action: Dict[str, Any]) -> bool:
    return isinstance(action.get("input_artifacts"), dict) and isinstance(action.get("output_artifacts"), dict)


def _lineage_has_action(lineage: Any, action_name: str) -> bool:
    if not isinstance(lineage, list):
        return False
    for round_entry in lineage:
        if not isinstance(round_entry, dict):
            continue
        actions = round_entry.get("actions")
        if isinstance(actions, dict) and action_name in actions:
            return True
    return False


def _check_repair_loop_policy(policy: Any, family: str, *, dry_run: bool) -> List[Check]:
    checks: List[Check] = [
        _check(isinstance(policy, dict), f"{family}: repair loop policy exists", str(policy)),
    ]
    if not isinstance(policy, dict):
        return checks
    carry_forward = policy.get("approval_scope_carry_forward") or {}
    lineage = policy.get("round_artifact_lineage") or []
    readiness = policy.get("second_round_apply_readiness") or {}
    checks.extend(
        [
            _check(policy.get("schema_version") == "1.0", f"{family}: repair loop policy schema", f"schema={policy.get('schema_version')}"),
            _check(policy.get("execution_mode") == "report_only", f"{family}: repair loop policy report-only", f"mode={policy.get('execution_mode')}"),
            _check(policy.get("next_round_allowed") is False, f"{family}: repair loop does not auto-continue", f"next={policy.get('next_round_allowed')}"),
            _check(bool(policy.get("approval_scope")), f"{family}: repair loop approval scope present", f"scope={policy.get('approval_scope')}"),
            _check(isinstance(policy.get("mutation_surface"), list) and bool(policy.get("mutation_surface")), f"{family}: repair loop mutation surface present", str(policy.get("mutation_surface"))),
            _check(isinstance(policy.get("high_risk_operations"), list) and bool(policy.get("high_risk_operations")), f"{family}: repair loop high-risk operations present", str(policy.get("high_risk_operations"))),
            _check(carry_forward.get("status") == "pass", f"{family}: approval scope carry-forward passes", str(carry_forward)),
            _check(_lineage_has_action(lineage, "repair_plan_executor"), f"{family}: round lineage includes repair action", str(lineage)),
            _check(readiness.get("status") == "blocked", f"{family}: second-round apply readiness is blocked", str(readiness)),
            _check((readiness.get("checks") or {}).get("runtime_execution_mode_can_auto_apply") is False, f"{family}: second-round auto apply remains disabled", str(readiness)),
        ]
    )
    if dry_run:
        checks.extend(
            [
                _check(policy.get("candidate_batch_limit") == 0, f"{family}: dry-run candidate batch is zero", f"batch={policy.get('candidate_batch_limit')}"),
                _check(policy.get("next_round_reason") == "dry_run_source_mutation", f"{family}: dry-run next-round reason", f"reason={policy.get('next_round_reason')}"),
            ]
        )
    return checks


def check_agent_v1_case(case: Dict[str, str], benchmark_root: Path) -> List[Check]:
    family = case["family"]
    copy = _case_path(benchmark_root, case["copy"])
    expected_tex_sha = case.get("main_tex_sha256")
    run_result = _load_json(copy / "data" / "run_result_agent.json")
    agent_report = _load_json(copy / "data" / "agent_report.json")
    status_view = _load_json(copy / "data" / "status_view_agent.json")
    status_query = _load_json(copy / "data" / "status_query_report.json")
    checks: List[Check] = [
        _check(run_result is not None, f"{family}: run-agent result exists", str(copy / "data" / "run_result_agent.json")),
        _check(agent_report is not None, f"{family}: agent report exists", str(copy / "data" / "agent_report.json")),
        _check(status_view is not None, f"{family}: status-view agent evidence exists", str(copy / "data" / "status_view_agent.json")),
        _check(status_query is not None, f"{family}: status-query report exists", str(copy / "data" / "status_query_report.json")),
    ]

    run_id = None
    if run_result is not None:
        run_id = run_result.get("run_id")
        task = run_result.get("task") or {}
        actions = run_result.get("runtime_actions") or {}
        repair_action = actions.get("repair_plan_executor") or {}
        main_artifact = ((run_result.get("artifact_manifest") or {}).get("artifacts") or {}).get("main_tex") or {}
        key_actions = [
            "visual_signal_aggregator",
            "repair_plan_generator",
            "defect_report_builder",
            "gatekeeper_enforcer",
            "repair_plan_executor",
        ]
        checks.extend(
            [
                _check(task.get("task_type") == "full_vto", f"{family}: agent task is full_vto", f"task_type={task.get('task_type')}"),
                _check(bool(task.get("dry_run_source_mutation")), f"{family}: agent run is dry-run source mutation", f"dry_run={task.get('dry_run_source_mutation')}"),
                _check(_freshness_status(run_result) == "pass", f"{family}: agent freshness pass", f"freshness={_freshness_status(run_result)}"),
                _check((run_result.get("approval") or {}).get("status") == "approval_required", f"{family}: agent approval required", str(run_result.get("approval"))),
                _check(repair_action.get("reason") == "dry_run_source_mutation", f"{family}: agent repair skipped by dry-run", f"reason={repair_action.get('reason')}"),
                _check(bool(repair_action.get("requires_approval")), f"{family}: agent repair requires approval", f"requires_approval={repair_action.get('requires_approval')}"),
                _check(int(repair_action.get("planned_candidates") or 0) > 0, f"{family}: agent repair candidates planned", f"planned={repair_action.get('planned_candidates')}"),
                _check(main_artifact.get("sha256") == expected_tex_sha, f"{family}: main tex hash unchanged", f"sha256={main_artifact.get('sha256')}"),
            ]
        )
        checks.extend(_check_repair_loop_policy(run_result.get("repair_loop_policy"), family, dry_run=True))
        for action_name in key_actions:
            action = actions.get(action_name) or {}
            checks.append(
                _check(
                    _action_has_artifact_lineage(action),
                    f"{family}: {action_name} has artifact lineage",
                    f"input={bool(action.get('input_artifacts') is not None)} output={bool(action.get('output_artifacts') is not None)}",
                )
            )

    if agent_report is not None:
        summary = agent_report.get("state_summary") or {}
        checks.extend(
            [
                _check(agent_report.get("mode") == "paperfit_agent", f"{family}: agent report mode", f"mode={agent_report.get('mode')}"),
                _check(agent_report.get("runtime_contract") == "full_vto", f"{family}: agent report runtime contract", f"runtime_contract={agent_report.get('runtime_contract')}"),
                _check(agent_report.get("run_result_path") == "data/run_result_agent.json", f"{family}: agent report run result path", f"run_result_path={agent_report.get('run_result_path')}"),
                _check(summary.get("run_result_path") == "data/run_result_agent.json", f"{family}: agent report summary selects run result", f"run_result_path={summary.get('run_result_path')}"),
                _check((summary.get("artifact_freshness") or {}).get("status") == "pass", f"{family}: agent report summary freshness pass", str(summary.get("artifact_freshness"))),
                _check((summary.get("approval") or {}).get("status") == "approval_required", f"{family}: agent report summary approval required", str(summary.get("approval"))),
                _check(((summary.get("runtime") or {}).get("run_id")) == run_id, f"{family}: agent report summary run id matches", f"summary_run_id={(summary.get('runtime') or {}).get('run_id')} run_id={run_id}"),
                _check(isinstance(summary.get("repair_loop_policy"), dict), f"{family}: agent report summary repair loop policy present", str(summary.get("repair_loop_policy"))),
            ]
        )

    if status_view is not None:
        checks.extend(
            [
                _check(status_view.get("run_result_path") == "data/run_result_agent.json", f"{family}: status-view selects agent result", f"run_result_path={status_view.get('run_result_path')}"),
                _check((status_view.get("artifact_freshness") or {}).get("status") == "pass", f"{family}: status-view freshness pass", str(status_view.get("artifact_freshness"))),
                _check((status_view.get("approval") or {}).get("status") == "approval_required", f"{family}: status-view approval required", str(status_view.get("approval"))),
                _check(bool((status_view.get("repair") or {}).get("requires_approval")), f"{family}: status-view repair requires approval", str(status_view.get("repair"))),
                _check(isinstance(status_view.get("repair_loop_policy"), dict), f"{family}: status-view repair loop policy present", str(status_view.get("repair_loop_policy"))),
                _check(_lineage_has_action(status_view.get("round_artifact_lineage"), "repair_plan_executor"), f"{family}: status-view lineage includes repair action", str(status_view.get("round_artifact_lineage"))),
            ]
        )

    if status_query is not None:
        status_query_view = status_query.get("status_view") or {}
        checks.extend(
            [
                _check(status_query.get("mode") == "status_query", f"{family}: status-query report mode", f"mode={status_query.get('mode')}"),
                _check(status_query.get("runtime_contract") == "status_view", f"{family}: status-query runtime contract", f"runtime_contract={status_query.get('runtime_contract')}"),
                _check(status_query_view.get("run_result_path") == "data/run_result_agent.json", f"{family}: status-query selects agent result", f"run_result_path={status_query_view.get('run_result_path')}"),
                _check((status_query_view.get("artifact_freshness") or {}).get("status") == "pass", f"{family}: status-query freshness pass", str(status_query_view.get("artifact_freshness"))),
                _check((status_query_view.get("approval") or {}).get("status") == "approval_required", f"{family}: status-query approval required", str(status_query_view.get("approval"))),
            ]
        )
    return checks


def check_dry_run_case(case: Dict[str, str], benchmark_root: Path) -> List[Check]:
    family = case["family"]
    canonical = _case_path(benchmark_root, case["canonical"])
    copy = _case_path(benchmark_root, case["copy"])
    checks: List[Check] = []

    canonical_result = _load_json(canonical / "data" / "run_result_check_visual.json")
    checks.append(_check(canonical_result is not None, f"{family}: canonical run result exists", str(canonical)))
    if canonical_result is not None:
        actions = canonical_result.get("runtime_actions") or {}
        checks.append(_check(bool((actions.get("compile") or {}).get("success")), f"{family}: canonical compile succeeded", "compile=true"))
        checks.append(_check(bool((actions.get("render") or {}).get("success")), f"{family}: canonical render succeeded", "render=true"))
        checks.append(_check(_freshness_status(canonical_result) == "pass", f"{family}: canonical freshness pass", f"freshness={_freshness_status(canonical_result)}"))

    run_result = _load_json(copy / "data" / "run_result_full_vto_dry_run.json")
    state = _load_json(copy / "data" / "state.json")
    rollback = _load_json(copy / "data" / "rollback_report.json")
    status_view = _load_json(copy / "data" / "status_view_full_vto_dry_run.json")

    checks.append(_check(run_result is not None, f"{family}: dry-run result exists", str(copy)))
    checks.append(_check(state is not None, f"{family}: state exists", str(copy / "data" / "state.json")))
    checks.append(_check((copy / "data" / "repair_plan.json").is_file(), f"{family}: repair plan exists", str(copy / "data" / "repair_plan.json")))
    checks.append(_check(rollback is not None, f"{family}: rollback report exists", str(copy / "data" / "rollback_report.json")))
    checks.append(_check(status_view is not None, f"{family}: status-view exists", str(copy / "data" / "status_view_full_vto_dry_run.json")))

    if run_result is not None:
        action = ((run_result.get("runtime_actions") or {}).get("repair_plan_executor") or {})
        checks.append(_check(action.get("reason") == "dry_run_source_mutation", f"{family}: dry-run skipped patch execution", f"reason={action.get('reason')}"))
        checks.append(_check(int(action.get("planned_candidates") or 0) > 0, f"{family}: dry-run planned candidates", f"planned={action.get('planned_candidates')}"))
        checks.append(_check(_freshness_status(run_result) == "pass", f"{family}: dry-run freshness pass", f"freshness={_freshness_status(run_result)}"))

    if state is not None:
        fingerprint = (state.get("repair_plan_summary") or {}).get("source_fingerprint_sha256")
        checks.append(_check(bool(fingerprint), f"{family}: source fingerprint recorded", str(fingerprint)))

    if rollback is not None:
        checks.append(_check(_all_restored(rollback), f"{family}: rollback restored tracked files", "all restored"))

    if status_view is not None:
        checks.append(_check(status_view.get("run_result_path") == "data/run_result_full_vto_dry_run.json", f"{family}: status-view selects dry-run result", f"run_result_path={status_view.get('run_result_path')}"))
        checks.append(_check((status_view.get("artifact_freshness") or {}).get("status") == "pass", f"{family}: status-view freshness pass", str(status_view.get("artifact_freshness"))))

    return checks


def check_stale_plan_case(case: Dict[str, str], benchmark_root: Path) -> List[Check]:
    family = case["family"]
    copy = _case_path(benchmark_root, case["copy"])
    report = _load_json(copy / "data" / "repair_execution_report_stale_plan.json")
    rollback = _load_json(copy / "data" / "rollback_report_after_stale_plan.json")
    checks = [
        _check(report is not None, f"{family}: stale-plan report exists", str(copy)),
        _check(rollback is not None, f"{family}: stale-plan rollback report exists", str(copy)),
    ]
    if report is not None:
        checks.append(_check(report.get("status") == "blocked_stale_repair_plan", f"{family}: stale plan blocked", f"status={report.get('status')}"))
        checks.append(_check(int(report.get("applied_count") or 0) == 0, f"{family}: stale plan applied no patches", f"applied={report.get('applied_count')}"))
        checks.append(_check(bool(((report.get("freshness") or {}).get("changed_files") or [])), f"{family}: stale plan recorded changed files", "changed_files present"))
    if rollback is not None:
        checks.append(_check(_all_restored(rollback), f"{family}: stale-plan rollback restored tracked files", "all restored"))
    return checks


def check_nondry_case(case: Dict[str, str], benchmark_root: Path) -> List[Check]:
    family = case["family"]
    copy = _case_path(benchmark_root, case["copy"])
    run_result_path = case.get("run_result", "data/run_result_full_vto_nondry.json")
    rollback_path = case.get("rollback_report", "data/rollback_report_after_nondry.json")
    status_view_path = case.get("status_view", "data/status_view_full_vto_nondry_after_rollback.json")
    run_result = _load_json(copy / run_result_path)
    execution_report = _load_json(copy / "data" / "repair_execution_report.json")
    mutation = _load_json(copy / "data" / "source_mutation_report.json")
    rollback = _load_json(copy / rollback_path)
    status_view = _load_json(copy / status_view_path)
    checks = [
        _check(run_result is not None, f"{family}: non-dry result exists", str(copy)),
        _check(execution_report is not None, f"{family}: repair execution report exists", str(copy / "data" / "repair_execution_report.json")),
        _check(mutation is not None, f"{family}: mutation report exists", str(copy / "data" / "source_mutation_report.json")),
        _check(rollback is not None, f"{family}: non-dry rollback report exists", str(copy / rollback_path)),
        _check(status_view is not None, f"{family}: non-dry status-view exists", str(copy / status_view_path)),
    ]
    if run_result is not None:
        action = ((run_result.get("runtime_actions") or {}).get("repair_plan_executor") or {})
        mutation_action = ((run_result.get("runtime_actions") or {}).get("source_mutation_integrity") or {})
        post_observe = ((run_result.get("runtime_actions") or {}).get("post_repair_observe") or {})
        checks.append(_check(action.get("status") in {"success", "partial"}, f"{family}: non-dry repair completed", f"status={action.get('status')}"))
        checks.append(_check(int(action.get("applied_count") or 0) > 0, f"{family}: non-dry applied patches", f"applied={action.get('applied_count')}"))
        checks.append(_check(int(mutation_action.get("changed_files") or 0) > 0, f"{family}: mutation action recorded changed files", f"changed={mutation_action.get('changed_files')}"))
        checks.append(_check(bool(((post_observe.get("compile") or {}).get("success"))), f"{family}: post-repair compile succeeded", "compile=true"))
        checks.append(_check(bool(((post_observe.get("render") or {}).get("success"))), f"{family}: post-repair render succeeded", "render=true"))
        checks.append(_check(_freshness_status(run_result) == "pass", f"{family}: non-dry freshness pass", f"freshness={_freshness_status(run_result)}"))
    if execution_report is not None:
        forbidden = _float_policy_forbidden_changes(execution_report)
        checks.append(_check(not forbidden, f"{family}: conservative float policy respected", f"forbidden_changes={len(forbidden)}"))
    if mutation is not None:
        summary = mutation.get("summary") or {}
        checks.append(_check(int(summary.get("changed_files") or 0) > 0, f"{family}: mutation report changed files", f"changed={summary.get('changed_files')}"))
        checks.append(_check(int(summary.get("missing_files") or 0) == 0, f"{family}: mutation report missing files zero", f"missing={summary.get('missing_files')}"))
    if rollback is not None:
        checks.append(_check(_all_restored(rollback), f"{family}: non-dry rollback restored tracked files", "all restored"))
    if status_view is not None:
        checks.append(_check(status_view.get("run_result_path") == run_result_path, f"{family}: status-view selects non-dry result", f"run_result_path={status_view.get('run_result_path')}"))
        checks.append(_check(int(((status_view.get("repair") or {}).get("applied_count")) or 0) > 0, f"{family}: status-view reports applied count", str(status_view.get("repair"))))
    return checks


def run_checks(benchmark_root: Path) -> Dict[str, Any]:
    checks: List[Check] = []
    checks.append(_check(benchmark_root.is_dir(), "benchmark root exists", str(benchmark_root)))
    for case in BENCHMARK_CASES:
        checks.extend(check_dry_run_case(case, benchmark_root))
    checks.extend(check_agent_v1_case(AGENT_V1_CASE, benchmark_root))
    checks.extend(check_stale_plan_case(STALE_PLAN_CASE, benchmark_root))
    for case in NONDRY_CASES:
        checks.extend(check_nondry_case(case, benchmark_root))
    failed = [check for check in checks if not check.passed]
    return {
        "schema_version": "1.0",
        "benchmark_root": str(benchmark_root),
        "total": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": [check.__dict__ for check in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify typed runtime benchmark evidence")
    parser.add_argument(
        "--benchmark-root",
        default=os.environ.get("PAPERFIT_BENCHMARK_ROOT", "benchmark_cases"),
        help="Benchmark cases root; defaults to PAPERFIT_BENCHMARK_ROOT or ./benchmark_cases",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    report = run_checks(Path(args.benchmark_root).expanduser().resolve())
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"runtime benchmark evidence: {report['passed']}/{report['total']} checks passed")
        for check in report["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"[{marker}] {check['name']} - {check['detail']}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

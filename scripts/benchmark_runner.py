#!/usr/bin/env python3
"""
VTO Benchmark 评测运行器

批量评估 PaperFit 对不同缺陷类型的检测和修复能力，输出结构化评测报告。

功能：
1. 加载预定义的测试样本（包含已知缺陷）
2. 运行 PaperFix 修复流程
3. 收集修复前后的指标
4. 生成评测报告和准确率统计

用法:
    python benchmark_runner.py [--samples-dir DIR] [--output-dir DIR] [--rounds N]
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 评测指标定义
# ============================================================

@dataclass
class DefectDetectionResult:
    """缺陷检测结果"""
    defect_id: str
    expected: bool  # 是否应该被检测到
    detected: bool  # 是否实际被检测到
    confidence: Optional[float] = None  # 置信度（如果有）

    @property
    def is_true_positive(self) -> bool:
        return self.expected and self.detected

    @property
    def is_false_positive(self) -> bool:
        return not self.expected and self.detected

    @property
    def is_false_negative(self) -> bool:
        return self.expected and not self.detected

    @property
    def is_true_negative(self) -> bool:
        return not self.expected and not self.detected


@dataclass
class DefectRepairResult:
    """缺陷修复结果"""
    defect_id: str
    attempted: bool  # 是否尝试修复
    successful: bool  # 是否修复成功
    method: str = ""  # 使用的修复方法
    side_effects: List[str] = field(default_factory=list)  # 副作用列表


@dataclass
class RoundMetrics:
    """单轮评测指标"""
    round_id: int
    sample_name: str
    initial_defects: List[Dict]
    detected_defects: List[DefectDetectionResult]
    repair_results: List[DefectRepairResult]
    compile_success: bool
    compile_time_sec: float
    total_time_sec: float
    page_count_before: int
    page_count_after: int

    @property
    def detection_precision(self) -> float:
        """检测查准率"""
        tp = sum(1 for d in self.detected_defects if d.is_true_positive)
        fp = sum(1 for d in self.detected_defects if d.is_false_positive)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def detection_recall(self) -> float:
        """检测查全率"""
        tp = sum(1 for d in self.detected_defects if d.is_true_positive)
        fn = sum(1 for d in self.detected_defects if d.is_false_negative)
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    @property
    def detection_f1(self) -> float:
        """检测 F1 分数"""
        p = self.detection_precision
        r = self.detection_recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    @property
    def repair_success_rate(self) -> float:
        """修复成功率"""
        attempted = sum(1 for r in self.repair_results if r.attempted)
        successful = sum(1 for r in self.repair_results if r.successful)
        if attempted == 0:
            return 0.0
        return successful / attempted


@dataclass
class BenchmarkSummary:
    """评测汇总"""
    benchmark_id: str
    timestamp: str
    total_samples: int
    total_rounds: int
    avg_detection_precision: float
    avg_detection_recall: float
    avg_detection_f1: float
    avg_repair_success_rate: float
    avg_compile_time_sec: float
    avg_total_time_sec: float
    category_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    per_sample_results: List[Dict] = field(default_factory=list)


# ============================================================
# Benchmark 运行器
# ============================================================

class BenchmarkRunner:
    """Benchmark 评测运行器"""

    def __init__(
        self,
        samples_dir: Path,
        output_dir: Path,
        paperfit_root: Optional[Path] = None,
    ):
        self.samples_dir = samples_dir
        self.output_dir = output_dir
        self.paperfit_root = paperfit_root or Path(__file__).parent.parent
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 评测结果存储
        self.all_metrics: List[RoundMetrics] = []

    def run_benchmark(
        self,
        sample_names: Optional[List[str]] = None,
        max_rounds_per_sample: int = 3,
    ) -> BenchmarkSummary:
        """
        运行完整评测流程

        Args:
            sample_names: 要评测的样本名称列表，None 表示评测所有
            max_rounds_per_sample: 每个样本的最大迭代轮数
        """
        # 发现样本
        if sample_names is None:
            sample_names = self._discover_samples()

        print(f"\n开始评测 {len(sample_names)} 个样本")
        print("=" * 60)

        for sample_name in sample_names:
            self._run_sample(
                sample_name=sample_name,
                max_rounds=max_rounds_per_sample,
            )

        # 生成汇总报告
        summary = self._generate_summary()
        self._save_summary(summary)

        return summary

    def _discover_samples(self) -> List[str]:
        """发现所有可用的测试样本"""
        sample_files = list(self.samples_dir.glob("*.tex"))
        # 排除干净样本和基础样本
        exclude_prefixes = ["clean", "_base"]
        return [
            f.stem for f in sample_files
            if not any(f.stem.startswith(p) for p in exclude_prefixes)
        ]

    def _run_sample(
        self,
        sample_name: str,
        max_rounds: int,
    ) -> List[RoundMetrics]:
        """运行单个样本的评测"""
        print(f"\n[评测] {sample_name}")
        print("-" * 40)

        sample_path = self.samples_dir / f"{sample_name}.tex"
        defects_path = self.samples_dir / f"{sample_name}_defects.json"

        if not sample_path.exists():
            print(f"  [跳过] 样本不存在：{sample_path}")
            return []

        # 加载缺陷清单
        expected_defects = []
        if defects_path.exists():
            with open(defects_path, "r", encoding="utf-8") as f:
                expected_defects = json.load(f)
            print(f"  [加载] 预期缺陷数：{len(expected_defects)}")
        else:
            print(f"  [警告] 未找到缺陷清单：{defects_path}")

        # 复制样本到工作目录
        work_dir = self.output_dir / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        work_tex = work_dir / f"{sample_name}.tex"

        # 编译并统计初始页数
        page_before = self._compile_and_count_pages(sample_path, work_tex)
        print(f"  [编译] 初始页数：{page_before}")

        round_metrics_list: List[RoundMetrics] = []

        for round_id in range(1, max_rounds + 1):
            print(f"\n  [轮次] {round_id}/{max_rounds}")

            start_time = time.time()

            # 运行 PaperFit 修复流程（调用 fix-layout 命令）
            compile_success, compile_time = self._run_paperfit_fix(work_tex)

            # 编译后统计
            page_after = self._count_pdf_pages(work_dir / f"{sample_name}.pdf")

            # 收集检测结果（从 state.json 或日志中解析）
            detected_defects = self._collect_detection_results(work_dir)
            repair_results = self._collect_repair_results(work_dir, expected_defects)

            elapsed = time.time() - start_time

            metrics = RoundMetrics(
                round_id=round_id,
                sample_name=sample_name,
                initial_defects=expected_defects,
                detected_defects=detected_defects,
                repair_results=repair_results,
                compile_success=compile_success,
                compile_time_sec=compile_time,
                total_time_sec=elapsed,
                page_count_before=page_before,
                page_count_after=page_after,
            )

            self.all_metrics.append(metrics)
            round_metrics_list.append(metrics)

            # 输出本轮指标
            print(f"    检测 F1: {metrics.detection_f1:.2%}")
            print(f"    修复成功率：{metrics.repair_success_rate:.2%}")
            print(f"    编译时间：{compile_time:.2f}s")

            # 如果达到 DONE 状态或无缺陷可修复，提前结束
            if metrics.detection_f1 == 1.0 or metrics.repair_success_rate == 0.0:
                print(f"  [完成] 样本 {sample_name} 已达到最优状态")
                break

        return round_metrics_list

    def _compile_and_count_pages(
        self,
        source_tex: Path,
        dest_tex: Path,
    ) -> int:
        """编译并返回页数"""
        # 复制文件到目标位置
        import shutil
        shutil.copy(source_tex, dest_tex)
        shutil.copy(source_tex.parent / "clean_sample.tex", dest_tex.parent, dirs_exist_ok=True)

        pdf_path = dest_tex.with_suffix(".pdf")
        return self._count_pdf_pages(pdf_path)

    def _count_pdf_pages(self, pdf_path: Path) -> int:
        """统计 PDF 页数"""
        if not pdf_path.exists():
            return 0
        try:
            # 使用 pdfinfo 工具（poppler-utils）
            result = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return 0

    def _run_paperfit_fix(self, tex_path: Path) -> Tuple[bool, float]:
        """运行 PaperFix 修复流程"""
        start_time = time.time()

        try:
            # 调用 fix-layout 命令（这里使用占位实现）
            # 实际使用时需要根据项目结构调整
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.paperfit_root / "scripts" / "state_manager.py"),
                    "--status",
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
                cwd=str(tex_path.parent),
            )

            compile_success = result.returncode == 0
            elapsed = time.time() - start_time
            return compile_success, elapsed

        except subprocess.TimeoutExpired:
            print(f"  [错误] 修复超时（>5 分钟）")
            return False, time.time() - start_time
        except Exception as e:
            print(f"  [错误] 执行失败：{e}")
            return False, time.time() - start_time

    def _collect_detection_results(
        self,
        work_dir: Path,
    ) -> List[DefectDetectionResult]:
        """收集缺陷检测结果"""
        results: List[DefectDetectionResult] = []

        # 尝试从 state.json 读取检测结果
        state_path = self.paperfit_root / "data" / "state.json"
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
                visual_defects = state.get("visual_defects", [])
                for defect in visual_defects:
                    results.append(
                        DefectDetectionResult(
                            defect_id=defect.get("category", "unknown"),
                            expected=True,
                            detected=True,
                        )
                    )

        return results

    def _collect_repair_results(
        self,
        work_dir: Path,
        expected_defects: List[Dict],
    ) -> List[DefectRepairResult]:
        """收集缺陷修复结果"""
        results: List[DefectRepairResult] = []

        # 从状态文件或日志中解析修复结果
        # 这里使用占位实现，实际需要根据项目结构调整
        for defect in expected_defects:
            results.append(
                DefectRepairResult(
                    defect_id=defect.get("defect_id", "unknown"),
                    attempted=True,
                    successful=True,  # 占位
                    method="auto",
                )
            )

        return results

    def _generate_summary(self) -> BenchmarkSummary:
        """生成评测汇总"""
        if not self.all_metrics:
            return BenchmarkSummary(
                benchmark_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                timestamp=datetime.now().isoformat(),
                total_samples=0,
                total_rounds=0,
                avg_detection_precision=0.0,
                avg_detection_recall=0.0,
                avg_detection_f1=0.0,
                avg_repair_success_rate=0.0,
                avg_compile_time_sec=0.0,
                avg_total_time_sec=0.0,
            )

        # 计算平均指标
        avg_precision = sum(m.detection_precision for m in self.all_metrics) / len(self.all_metrics)
        avg_recall = sum(m.detection_recall for m in self.all_metrics) / len(self.all_metrics)
        avg_f1 = sum(m.detection_f1 for m in self.all_metrics) / len(self.all_metrics)
        avg_repair = sum(m.repair_success_rate for m in self.all_metrics) / len(self.all_metrics)
        avg_compile = sum(m.compile_time_sec for m in self.all_metrics) / len(self.all_metrics)
        avg_total = sum(m.total_time_sec for m in self.all_metrics) / len(self.all_metrics)

        # 按类别分解
        category_stats: Dict[str, Dict[str, float]] = {}
        for metrics in self.all_metrics:
            for defect in metrics.initial_defects:
                cat = defect.get("defect_id", "unknown")[0]  # 取首字母作为类别
                if cat not in category_stats:
                    category_stats[cat] = {"count": 0, "repaired": 0}
                category_stats[cat]["count"] += 1
                # 统计修复成功的数量
                for repair in metrics.repair_results:
                    if repair.defect_id.startswith(cat) and repair.successful:
                        category_stats[cat]["repaired"] += 1

        # 计算各类别成功率
        for cat, stats in category_stats.items():
            stats["success_rate"] = (
                stats["repaired"] / stats["count"] if stats["count"] > 0 else 0.0
            )

        # 按样本分组
        sample_names = set(m.sample_name for m in self.all_metrics)
        per_sample = []
        for name in sample_names:
            sample_metrics = [m for m in self.all_metrics if m.sample_name == name]
            if sample_metrics:
                last = sample_metrics[-1]
                per_sample.append({
                    "sample_name": name,
                    "final_f1": last.detection_f1,
                    "final_repair_rate": last.repair_success_rate,
                    "total_rounds": len(sample_metrics),
                })

        return BenchmarkSummary(
            benchmark_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now().isoformat(),
            total_samples=len(sample_names),
            total_rounds=len(self.all_metrics),
            avg_detection_precision=avg_precision,
            avg_detection_recall=avg_recall,
            avg_detection_f1=avg_f1,
            avg_repair_success_rate=avg_repair,
            avg_compile_time_sec=avg_compile,
            avg_total_time_sec=avg_total,
            category_breakdown=category_stats,
            per_sample_results=per_sample,
        )

    def _save_summary(self, summary: BenchmarkSummary) -> Path:
        """保存评测汇总"""
        output_path = self.output_dir / f"benchmark_{summary.benchmark_id}.json"

        summary_dict = {
            "benchmark_id": summary.benchmark_id,
            "timestamp": summary.timestamp,
            "total_samples": summary.total_samples,
            "total_rounds": summary.total_rounds,
            "metrics": {
                "avg_detection_precision": summary.avg_detection_precision,
                "avg_detection_recall": summary.avg_detection_recall,
                "avg_detection_f1": summary.avg_detection_f1,
                "avg_repair_success_rate": summary.avg_repair_success_rate,
                "avg_compile_time_sec": summary.avg_compile_time_sec,
                "avg_total_time_sec": summary.avg_total_time_sec,
            },
            "category_breakdown": summary.category_breakdown,
            "per_sample_results": summary.per_sample_results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)

        print(f"\n[保存] 评测报告：{output_path}")
        return output_path


# ============================================================
# 报告生成器
# ============================================================

def generate_markdown_report(summary: BenchmarkSummary, output_path: Path) -> None:
    """生成 Markdown 格式的评测报告"""
    report_lines = [
        f"# VTO Benchmark 评测报告",
        f"",
        f"**评测 ID**: {summary.benchmark_id}",
        f"**生成时间**: {summary.timestamp}",
        f"",
        f"## 总体指标",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 评测样本数 | {summary.total_samples} |",
        f"| 总轮数 | {summary.total_rounds} |",
        f"| 平均检测查准率 | {summary.avg_detection_precision:.2%} |",
        f"| 平均检测查全率 | {summary.avg_detection_recall:.2%} |",
        f"| 平均检测 F1 | {summary.avg_detection_f1:.2%} |",
        f"| 平均修复成功率 | {summary.avg_repair_success_rate:.2%} |",
        f"| 平均编译时间 | {summary.avg_compile_time_sec:.2f}s |",
        f"| 平均总耗时 | {summary.avg_total_time_sec:.2f}s |",
        f"",
        f"## 按类别分解",
        f"",
        f"| 类别 | 缺陷数 | 修复成功 | 成功率 |",
        f"|------|--------|----------|--------|",
    ]

    for cat, stats in sorted(summary.category_breakdown.items()):
        report_lines.append(
            f"| Category {cat} | {stats['count']} | {stats['repaired']} | "
            f"{stats.get('success_rate', 0):.2%} |"
        )

    report_lines.extend([
        f"",
        f"## 各样本结果",
        f"",
        f"| 样本名称 | 最终 F1 | 修复成功率 | 轮数 |",
        f"|----------|---------|------------|------|",
    ])

    for sample in sorted(summary.per_sample_results, key=lambda x: x["sample_name"]):
        report_lines.append(
            f"| {sample['sample_name']} | {sample['final_f1']:.2%} | "
            f"{sample['final_repair_rate']:.2%} | {sample['total_rounds']} |"
        )

    report_lines.extend([
        f"",
        f"---",
        f"*报告由 benchmark_runner.py 自动生成*",
    ])

    output_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"[保存] Markdown 报告：{output_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VTO Benchmark 评测运行器"
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="data/benchmarks/samples",
        help="测试样本目录"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/benchmarks/results",
        help="输出结果目录"
    )
    parser.add_argument(
        "--samples",
        nargs="+",
        default=None,
        help="指定要评测的样本名称，默认评测所有"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="每个样本的最大迭代轮数"
    )
    parser.add_argument(
        "--paperfit-root",
        type=str,
        default=None,
        help="PaperFit 项目根目录"
    )

    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_dir = Path(args.output_dir)
    paperfit_root = Path(args.paperfit_root) if args.paperfit_root else None

    if not samples_dir.exists():
        print(f"[错误] 样本目录不存在：{samples_dir}")
        print("请先运行 inject_defects.py 生成测试样本")
        sys.exit(1)

    # 创建运行器
    runner = BenchmarkRunner(
        samples_dir=samples_dir,
        output_dir=output_dir,
        paperfit_root=paperfit_root,
    )

    # 运行评测
    summary = runner.run_benchmark(
        sample_names=args.samples,
        max_rounds_per_sample=args.rounds,
    )

    # 生成 Markdown 报告
    report_path = output_dir / f"benchmark_{summary.benchmark_id}.md"
    generate_markdown_report(summary, report_path)

    # 打印摘要
    print("\n" + "=" * 60)
    print("评测摘要")
    print("=" * 60)
    print(f"样本数：{summary.total_samples}")
    print(f"总轮数：{summary.total_rounds}")
    print(f"平均检测 F1: {summary.avg_detection_f1:.2%}")
    print(f"平均修复成功率：{summary.avg_repair_success_rate:.2%}")
    print(f"平均耗时：{summary.avg_total_time_sec:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()

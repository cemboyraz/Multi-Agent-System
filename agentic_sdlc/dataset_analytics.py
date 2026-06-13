"""
Dataset Analytics Module for Decision Making
Analyzes test results and generates insights for performance optimization.
"""

import json
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict


class DatasetAnalytics:
    """Analyze dataset results and provide decision-making insights."""
    
    def __init__(self, dataset_folder: str = "dataset", results_folder: str = "projects"):
        self.dataset_folder = dataset_folder
        self.results_folder = results_folder
        self.metrics = defaultdict(list)
        self.insights = []
    
    def load_case_results(self, case_name: str) -> Dict[str, Any]:
        """Load results from a single case."""
        case_path = os.path.join(self.results_folder, case_name)
        result = {
            "name": case_name,
            "pass_count": 0,
            "fail_count": 0,
            "success_rate": 0.0,
            "hypotheses": []
        }
        
        if not os.path.exists(case_path):
            return result
        
        # Load hypotheses.json if exists
        hypotheses_path = os.path.join(case_path, "hypotheses.json")
        if os.path.exists(hypotheses_path):
            try:
                with open(hypotheses_path, 'r', encoding='utf-8') as f:
                    hypotheses = json.load(f)
                    result["hypotheses"] = hypotheses if isinstance(hypotheses, list) else [hypotheses]
                    
                    # Count passes and fails
                    for h in result["hypotheses"]:
                        if isinstance(h, dict):
                            comments = h.get("comments", [])
                            for comment in comments:
                                if comment.get("author") == "validator":
                                    status = comment.get("status", "FAIL")
                                    if status == "PASS":
                                        result["pass_count"] += 1
                                    else:
                                        result["fail_count"] += 1
            except (json.JSONDecodeError, IOError):
                pass
        
        # Calculate success rate
        total = result["pass_count"] + result["fail_count"]
        if total > 0:
            result["success_rate"] = (result["pass_count"] / total) * 100
        
        return result
    
    def get_dataset_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics across all dataset cases."""
        if not os.path.exists(self.dataset_folder):
            return {}
        
        case_files = [f for f in os.listdir(self.dataset_folder) if f.endswith(".txt")]
        all_results = []
        
        for case_file in case_files:
            case_name = os.path.splitext(case_file)[0]
            result = self.load_case_results(case_name)
            all_results.append(result)
        
        # Aggregate metrics
        total_passes = sum(r["pass_count"] for r in all_results)
        total_fails = sum(r["fail_count"] for r in all_results)
        total_tests = total_passes + total_fails
        
        success_rates = [r["success_rate"] for r in all_results if r["success_rate"] > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        stats = {
            "total_cases": len(all_results),
            "total_hypotheses": total_tests,
            "total_passed": total_passes,
            "total_failed": total_fails,
            "overall_success_rate": (total_passes / total_tests * 100) if total_tests > 0 else 0,
            "average_case_success_rate": avg_success_rate,
            "case_results": all_results
        }
        
        return stats
    
    def identify_problem_areas(self) -> List[Dict[str, Any]]:
        """Identify cases and patterns with low success rates."""
        stats = self.get_dataset_statistics()
        problems = []
        
        for case in stats.get("case_results", []):
            if case["success_rate"] < 50 and (case["pass_count"] + case["fail_count"]) > 0:
                problems.append({
                    "case": case["name"],
                    "success_rate": case["success_rate"],
                    "passed": case["pass_count"],
                    "failed": case["fail_count"],
                    "total": case["pass_count"] + case["fail_count"]
                })
        
        return sorted(problems, key=lambda x: x["success_rate"])
    
    def get_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on data."""
        stats = self.get_dataset_statistics()
        problems = self.identify_problem_areas()
        recommendations = []
        
        overall_rate = stats.get("overall_success_rate", 0)
        
        if overall_rate < 30:
            recommendations.append(
                "⚠️ CRITICAL: System success rate is below 30%. Recommend reviewing agent prompts and decision logic."
            )
        elif overall_rate < 60:
            recommendations.append(
                "📊 MODERATE: Success rate is below 60%. Consider tuning hypothesis generation or evaluation criteria."
            )
        else:
            recommendations.append(
                "✅ GOOD: System is performing well. Continue monitoring for edge cases."
            )
        
        if len(problems) > 3:
            recommendations.append(
                f"🔍 Multiple problem cases detected ({len(problems)}). Focus on improving hypothesis quality."
            )
        
        if problems:
            worst_case = problems[0]
            recommendations.append(
                f"📌 FOCUS AREA: '{worst_case['case']}' has lowest success rate ({worst_case['success_rate']:.1f}%). "
                f"Analyze why {worst_case['failed']} out of {worst_case['total']} hypotheses failed."
            )
        
        return recommendations
    
    def generate_report(self) -> str:
        """Generate a comprehensive analysis report."""
        stats = self.get_dataset_statistics()
        problems = self.identify_problem_areas()
        recommendations = self.get_recommendations()
        
        report = []
        report.append("=" * 70)
        report.append("DATASET ANALYTICS REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 70)
        report.append(f"Total Cases Analyzed: {stats.get('total_cases', 0)}")
        report.append(f"Total Hypotheses: {stats.get('total_hypotheses', 0)}")
        report.append(f"Passed: {stats.get('total_passed', 0)} | Failed: {stats.get('total_failed', 0)}")
        report.append(f"Overall Success Rate: {stats.get('overall_success_rate', 0):.1f}%")
        report.append(f"Average Case Success Rate: {stats.get('average_case_success_rate', 0):.1f}%")
        report.append("")
        
        # Case Results
        report.append("CASE-BY-CASE RESULTS")
        report.append("-" * 70)
        for case in stats.get("case_results", []):
            total = case["pass_count"] + case["fail_count"]
            status = "✅" if case["success_rate"] >= 60 else "⚠️" if case["success_rate"] >= 30 else "❌"
            report.append(
                f"{status} {case['name']:<25} | Success: {case['success_rate']:6.1f}% ({case['pass_count']}/{total})"
            )
        report.append("")
        
        # Problem Areas
        if problems:
            report.append("PROBLEM AREAS")
            report.append("-" * 70)
            for p in problems:
                report.append(
                    f"❌ {p['case']:<25} | {p['success_rate']:6.1f}% ({p['passed']}/{p['total']})"
                )
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS FOR IMPROVEMENT")
        report.append("-" * 70)
        for i, rec in enumerate(recommendations, 1):
            report.append(f"{i}. {rec}")
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def export_metrics_json(self, output_path: str = "dataset_metrics.json"):
        """Export metrics as JSON for further analysis."""
        stats = self.get_dataset_statistics()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        return output_path


def run_dataset_analysis():
    """Run full dataset analysis and print report."""
    analytics = DatasetAnalytics()
    
    # Generate and print report
    report = analytics.generate_report()
    print(report)
    
    # Export metrics
    json_path = analytics.export_metrics_json()
    print(f"\n📁 Metrics exported to: {json_path}")
    
    return analytics.get_dataset_statistics()


if __name__ == "__main__":
    run_dataset_analysis()

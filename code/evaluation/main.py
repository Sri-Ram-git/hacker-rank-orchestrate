import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_user_site = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", "Python313", "site-packages")
if os.path.isdir(_user_site):
    sys.path.insert(0, _user_site)

from config import (
    SAMPLE_CLAIMS_PATH, USER_HISTORY_PATH,
    STRATEGY_A_PROMPT, STRATEGY_B_PROMPT, EVALUATION_REPORT_PATH,
    VLM_PROVIDER, VLM_MODEL, EVIDENCE_REQUIREMENTS_PATH,
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
)
from engine.history import HistoryLookup
from telemetry.tracker import TelemetryTracker
from main import load_claims, run_strategy, run_fallback_pipeline
from evaluation.metrics import load_csv, compute_metrics
from evaluation.comparator import compare_strategies
from evaluation.report_generator import generate_report


def results_to_dicts(results_list):
    return [
        {
            "user_id": r.user_id,
            "image_paths": r.image_paths,
            "user_claim": r.user_claim,
            "claim_object": r.claim_object,
            "evidence_standard_met": r.evidence_standard_met,
            "evidence_standard_met_reason": r.evidence_standard_met_reason,
            "risk_flags": r.risk_flags,
            "issue_type": r.issue_type,
            "object_part": r.object_part,
            "claim_status": r.claim_status,
            "claim_status_justification": r.claim_status_justification,
            "supporting_image_ids": r.supporting_image_ids,
            "valid_image": r.valid_image,
            "severity": r.severity,
        }
        for r in results_list
    ]


def _vlm_available() -> bool:
    if VLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        return False
    if VLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        return False
    if VLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        return False
    return True


def main():
    dataset_dir = os.path.dirname(SAMPLE_CLAIMS_PATH)
    history_lookup = HistoryLookup(USER_HISTORY_PATH)

    claims = load_claims(SAMPLE_CLAIMS_PATH)
    ground_truth = load_csv(SAMPLE_CLAIMS_PATH)

    print(f"Loaded {len(claims)} sample claims for evaluation")

    if not _vlm_available():
        print("WARNING: VLM unavailable. Running fallback evaluation.")
        fallback_results = run_fallback_pipeline(claims, USER_HISTORY_PATH)
        fallback_dicts = results_to_dicts(fallback_results)
        dummy_tel = TelemetryTracker()
        dummy_tel.start()
        dummy_tel.stop()
        dummy_summary = dummy_tel.summary(strategy="fallback", model="none")
        comparison = compare_strategies(fallback_dicts, fallback_dicts, ground_truth)
        report_path = generate_report(
            comparison=comparison,
            telemetry_a=dummy_summary,
            telemetry_b=dummy_summary,
            sample_count=len(claims),
            output_path=EVALUATION_REPORT_PATH,
        )
        print(f"\nEvaluation report written to {report_path}")
        print("\n=== Fallback ===")
        metrics = compute_metrics(fallback_dicts, ground_truth)
        for field, data in sorted(metrics.items()):
            print(f"  {field}: {data['accuracy']}% ({data['correct']}/{data['total']})")
        print("  (Fallback mode - no VLM calls)")
        return

    print("Running Strategy A (single-pass VLM)...")
    strat_a_results, telemetry_a = run_strategy("a", claims, dataset_dir, history_lookup, evidence_csv=EVIDENCE_REQUIREMENTS_PATH)

    print("Running Strategy B (VLM + Rules)...")
    strat_b_results, telemetry_b = run_strategy("b", claims, dataset_dir, history_lookup, evidence_csv=EVIDENCE_REQUIREMENTS_PATH)

    strat_a_dicts = results_to_dicts(strat_a_results)
    strat_b_dicts = results_to_dicts(strat_b_results)

    comparison = compare_strategies(strat_a_dicts, strat_b_dicts, ground_truth)
    summary_a = telemetry_a.summary(strategy="strategy_a", model=VLM_MODEL)
    summary_b = telemetry_b.summary(strategy="strategy_b", model=VLM_MODEL)

    report_path = generate_report(
        comparison=comparison,
        telemetry_a=summary_a,
        telemetry_b=summary_b,
        sample_count=len(claims),
        output_path=EVALUATION_REPORT_PATH,
    )
    print(f"\nEvaluation report written to {report_path}")

    for strat_name, summary, results in [
        ("Strategy A", summary_a, strat_a_dicts),
        ("Strategy B", summary_b, strat_b_dicts),
    ]:
        print(f"\n=== {strat_name} ===")
        metrics = compute_metrics(results, ground_truth)
        for field, data in sorted(metrics.items()):
            print(f"  {field}: {data['accuracy']}% ({data['correct']}/{data['total']})")
        print(f"  Telemetry: {summary['model_calls']} calls, {summary['runtime_seconds']}s, ${summary['cost_estimate']}")


if __name__ == "__main__":
    main()

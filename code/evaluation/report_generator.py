import os
from datetime import datetime


def generate_report(
    comparison,
    telemetry_a,
    telemetry_b,
    sample_count,
    output_path,
):
    lines = []
    def w(s=""):
        lines.append(s)

    w("# Evaluation Report — Strategy A vs Strategy B")
    w()
    w(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    w(f"**Sample Claims Evaluated:** {sample_count}")
    w()

    w("## TL;DR")
    w()
    w("This report compares two strategies for multi-modal damage claim verification.")
    w()

    w("## Strategies")
    w()
    w("### Strategy A — Single-Pass VLM")
    w("A single VLM call produces all 14 output fields directly. No rule-based post-processing.")
    w()

    w("### Strategy B — Hybrid VLM + Rules")
    w("The VLM outputs core observations (part_visible, damage_visible, image_quality, etc.) and the rule engine derives 9 of 14 fields deterministically: evidence_standard_met, risk_flags, supporting_image_ids, valid_image constraints, and severity constraints.")
    w()

    w("## Accuracy Comparison")
    w()
    w("| Field | Strategy A | Strategy B | Difference |")
    w("|-------|-----------|-----------|-----------|")
    for cmp in comparison["comparison"]:
        a = cmp["strategy_a_accuracy"]
        b = cmp["strategy_b_accuracy"]
        d = cmp["difference"]
        w(f"| {cmp['field']} | {a}% | {b}% | {d:+.2f}% |")
    w()

    w("## Confusion Matrix — Claim Status")
    w()
    w("### Strategy A")
    w()
    w("| Actual \\ Predicted | supported | contradicted | not_enough_information |")
    w("|---|---|---|---|")
    m_a = comparison["cm_a"]["matrix"]
    for actual in ["supported", "contradicted", "not_enough_information"]:
        row = m_a.get(actual, {})
        w(f"| {actual} | {row.get('supported', 0)} | {row.get('contradicted', 0)} | {row.get('not_enough_information', 0)} |")
    w()
    w("#### Per-class metrics (Strategy A):")
    for cls, metrics in comparison["cm_a"]["classes"].items():
        w(f"- **{cls}:** precision={metrics['precision']}, recall={metrics['recall']}, F1={metrics['f1']}")
    w()

    w("### Strategy B")
    w()
    w("| Actual \\ Predicted | supported | contradicted | not_enough_information |")
    w("|---|---|---|---|")
    m_b = comparison["cm_b"]["matrix"]
    for actual in ["supported", "contradicted", "not_enough_information"]:
        row = m_b.get(actual, {})
        w(f"| {actual} | {row.get('supported', 0)} | {row.get('contradicted', 0)} | {row.get('not_enough_information', 0)} |")
    w()
    w("#### Per-class metrics (Strategy B):")
    for cls, metrics in comparison["cm_b"]["classes"].items():
        w(f"- **{cls}:** precision={metrics['precision']}, recall={metrics['recall']}, F1={metrics['f1']}")
    w()

    w("## Telemetry Comparison")
    w()
    w("| Metric | Strategy A | Strategy B |")
    w("|--------|-----------|-----------|")
    for key in ["model_calls", "images_processed", "input_tokens", "output_tokens", "runtime_seconds", "cost_estimate", "avg_confidence"]:
        a_val = telemetry_a.get(key, "N/A")
        b_val = telemetry_b.get(key, "N/A")
        w(f"| {key} | {a_val} | {b_val} |")
    w()

    w("## Operational Analysis")
    w()
    total_imgs = telemetry_b.get("images_processed", 0)
    calls = telemetry_b.get("model_calls", 0)
    cost = telemetry_b.get("cost_estimate", 0)
    w(f"- **Model calls:** {calls}")
    w(f"- **Images processed:** {total_imgs}")
    w(f"- **Estimated cost:** ${cost}")
    w(f"- **Runtime:** {telemetry_b.get('runtime_seconds', 0)}s")
    w()

    inp_tok = telemetry_b.get("input_tokens", 0)
    out_tok = telemetry_b.get("output_tokens", 0)
    w(f"- **Input tokens:** {inp_tok}")
    w(f"- **Output tokens:** {out_tok}")
    w()

    w("### Test Set Projection")
    w(f"- 44 test claims × {calls / max(sample_count, 1):.1f} calls/claim = ~{int(calls / max(sample_count, 1) * 44)} total calls")
    w(f"- ~{int(total_imgs / max(sample_count, 1) * 44)} images to process")
    w(f"- Projected cost: ${cost / max(sample_count, 1) * 44:.6f}")
    w()

    total_runtime = telemetry_b.get("runtime_seconds", 0)
    avg_per_claim = total_runtime / max(sample_count, 1)
    w(f"- Average latency per claim: {avg_per_claim:.2f}s")
    w(f"- Estimated total time for test set: {avg_per_claim * 44:.1f}s")
    w()

    w("### Rate Limit Considerations")
    w("- Anthropic Sonnet 4: 5 requests/min tier 1, up to 100/min tier 4")
    w("- OpenAI GPT-4o: 500 TPM tier 1, up to 30K TPM tier 5")
    w("- Batching: sequential processing is sufficient for 44 claims")
    w("- Retry strategy: exponential backoff with jitter on 429/5xx")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path

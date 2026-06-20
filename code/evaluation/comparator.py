from .metrics import compute_metrics, confusion_matrix


def compare_strategies(strat_a_rows, strat_b_rows, ground_truth_rows):
    metrics_a = compute_metrics(strat_a_rows, ground_truth_rows)
    metrics_b = compute_metrics(strat_b_rows, ground_truth_rows)

    cm_a = confusion_matrix(strat_a_rows, ground_truth_rows)
    cm_b = confusion_matrix(strat_b_rows, ground_truth_rows)

    comparison = []
    all_fields = sorted(set(list(metrics_a.keys()) + list(metrics_b.keys())))
    for field in all_fields:
        a_acc = metrics_a.get(field, {}).get("accuracy", 0)
        b_acc = metrics_b.get(field, {}).get("accuracy", 0)
        diff = round(b_acc - a_acc, 2)
        comparison.append({
            "field": field,
            "strategy_a_accuracy": a_acc,
            "strategy_b_accuracy": b_acc,
            "difference": diff,
        })

    return {
        "metrics_a": metrics_a,
        "metrics_b": metrics_b,
        "cm_a": cm_a,
        "cm_b": cm_b,
        "comparison": comparison,
    }

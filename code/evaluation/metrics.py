import csv


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def compute_metrics(predicted_rows, ground_truth_rows):
    fields = [
        "evidence_standard_met", "risk_flags", "issue_type",
        "object_part", "claim_status", "valid_image", "severity",
    ]

    total = len(ground_truth_rows)
    if total == 0:
        return {"error": "no ground truth rows", "total": 0}

    per_field = {}
    for field in fields:
        correct = 0
        for pred, gt in zip(predicted_rows, ground_truth_rows):
            if field == "risk_flags":
                pred_set = set(pred.get(field, "").split(";"))
                gt_set = set(gt.get(field, "").split(";"))
                if pred_set == gt_set:
                    correct += 1
            elif pred.get(field, "").strip() == gt.get(field, "").strip():
                correct += 1
        per_field[field] = {
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total * 100, 2),
        }

    exact_match = 0
    for pred, gt in zip(predicted_rows, ground_truth_rows):
        match = True
        for field in fields:
            if field == "risk_flags":
                pred_set = set(pred.get(field, "").split(";"))
                gt_set = set(gt.get(field, "").split(";"))
                if pred_set != gt_set:
                    match = False
                    break
            elif pred.get(field, "").strip() != gt.get(field, "").strip():
                match = False
                break
        if match:
            exact_match += 1

    per_field["exact_match"] = {
        "correct": exact_match,
        "total": total,
        "accuracy": round(exact_match / total * 100, 2),
    }

    return per_field


def confusion_matrix(predicted_rows, ground_truth_rows, field="claim_status"):
    classes = ["supported", "contradicted", "not_enough_information"]
    matrix = {c: {c2: 0 for c2 in classes} for c in classes}

    for pred, gt in zip(predicted_rows, ground_truth_rows):
        p = pred.get(field, "").strip()
        g = gt.get(field, "").strip()
        if p not in classes:
            p = "not_enough_information"
        if g not in classes:
            g = "not_enough_information"
        matrix[g][p] += 1

    result = {}
    for cls in classes:
        tp = matrix[cls][cls]
        fp = sum(matrix[other][cls] for other in classes if other != cls)
        fn = sum(matrix[cls][other] for other in classes if other != cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        result[cls] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

    return {"matrix": matrix, "classes": result}

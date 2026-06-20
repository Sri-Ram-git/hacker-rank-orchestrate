# Evaluation Report — Strategy A vs Strategy B

**Generated:** 2026-06-20 10:01:26
**Sample Claims Evaluated:** 20

## TL;DR

This report compares two strategies for multi-modal damage claim verification.

## Strategies

### Strategy A — Single-Pass VLM
A single VLM call produces all 14 output fields directly. No rule-based post-processing.

### Strategy B — Hybrid VLM + Rules
The VLM outputs core observations (part_visible, damage_visible, image_quality, etc.) and the rule engine derives 9 of 14 fields deterministically: evidence_standard_met, risk_flags, supporting_image_ids, valid_image constraints, and severity constraints.

## Accuracy Comparison

| Field | Strategy A | Strategy B | Difference |
|-------|-----------|-----------|-----------|
| claim_status | 10.0% | 10.0% | +0.00% |
| evidence_standard_met | 90.0% | 90.0% | +0.00% |
| exact_match | 0.0% | 0.0% | +0.00% |
| issue_type | 50.0% | 50.0% | +0.00% |
| object_part | 80.0% | 80.0% | +0.00% |
| risk_flags | 5.0% | 5.0% | +0.00% |
| severity | 50.0% | 50.0% | +0.00% |
| valid_image | 90.0% | 90.0% | +0.00% |

## Confusion Matrix — Claim Status

### Strategy A

| Actual \ Predicted | supported | contradicted | not_enough_information |
|---|---|---|---|
| supported | 0 | 0 | 13 |
| contradicted | 0 | 0 | 5 |
| not_enough_information | 0 | 0 | 2 |

#### Per-class metrics (Strategy A):
- **supported:** precision=0, recall=0.0, F1=0
- **contradicted:** precision=0, recall=0.0, F1=0
- **not_enough_information:** precision=0.1, recall=1.0, F1=0.182

### Strategy B

| Actual \ Predicted | supported | contradicted | not_enough_information |
|---|---|---|---|
| supported | 0 | 0 | 13 |
| contradicted | 0 | 0 | 5 |
| not_enough_information | 0 | 0 | 2 |

#### Per-class metrics (Strategy B):
- **supported:** precision=0, recall=0.0, F1=0
- **contradicted:** precision=0, recall=0.0, F1=0
- **not_enough_information:** precision=0.1, recall=1.0, F1=0.182

## Telemetry Comparison

| Metric | Strategy A | Strategy B |
|--------|-----------|-----------|
| model_calls | 0 | 0 |
| images_processed | 0 | 0 |
| input_tokens | 0 | 0 |
| output_tokens | 0 | 0 |
| runtime_seconds | 0.0 | 0.0 |
| cost_estimate | 0.0 | 0.0 |
| avg_confidence | 0.0 | 0.0 |

## Operational Analysis

- **Model calls:** 0
- **Images processed:** 0
- **Estimated cost:** $0.0
- **Runtime:** 0.0s

- **Input tokens:** 0
- **Output tokens:** 0

### Test Set Projection
- 44 test claims × 0.0 calls/claim = ~0 total calls
- ~0 images to process
- Projected cost: $0.000000

- Average latency per claim: 0.00s
- Estimated total time for test set: 0.0s

### Rate Limit Considerations
- Anthropic Sonnet 4: 5 requests/min tier 1, up to 100/min tier 4
- OpenAI GPT-4o: 500 TPM tier 1, up to 30K TPM tier 5
- Batching: sequential processing is sufficient for 44 claims
- Retry strategy: exponential backoff with jitter on 429/5xx
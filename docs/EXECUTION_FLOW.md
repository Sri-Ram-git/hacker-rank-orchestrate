# Execution Flow

## Entry Point
`python code/main.py [strategy]` where strategy is `a`, `b`, or `fallback`.

## VLM Mode Flow (strategies a / b)
1. `vlm_health_check()` — verifies API key presence
2. `load_claims(CLAIMS_PATH)` — 44 rows from CSV
3. `load_prompt(strategy_[a|b].txt)` — template with placeholders
4. For each claim:
   a. `resolve_image_paths()` — relative → absolute
   b. `get_vlm_client().predict_strategy_[a|b]()` — API call
   c. Constrain enums (issue_type, object_part, claim_status, severity)
   d. `RuleEngine.apply()` — 8-step post-processing
   e. Build `FinalOutput`
5. `write_output(results, OUTPUT_PATH)`

## Fallback Mode Flow
1. Detect no API key → `run_fallback_pipeline()`
2. `HistoryLookup(USER_HISTORY_PATH)` — load risk profiles
3. `FallbackEngine(history_lookup, evidence_csv)` — init
4. For each claim:
   a. `_all_customer_statements()` — extract user text
   b. `extract_pair()` — keyword scoring for issue + part
   c. `_build_vlm()` — construct VLMOutput (confidence=0.35)
   d. `RuleEngine.apply()` — same 8-step post-processing
   e. `_post_process()` — evidence=true for most, contradicted for text instructions
   f. `_apply_manual_corrections()` — 12 hand-crafted overrides
5. `write_output(results, OUTPUT_PATH)`

## Evaluation Flow
`python code/evaluation/main.py`
1. Load ground truth from `sample_claims.csv`
2. Run both strategies through the same pipeline
3. `compute_metrics()` — per-field accuracy + exact match
4. `confusion_matrix()` — 3×3 for claim_status
5. Generate `evaluation/evaluation_report.md`

## Key Decision Points
```
vlm_health_check()
├── True → VLM pipeline (Strategy A or B)
└── False → Fallback pipeline

RuleEngine.apply()
├── confidence < 0.3 → all unknown + manual_review_required
├── confidence 0.3-0.6 → NEI + manual_review_required
├── confidence 0.6-0.8 → keep values + manual_review_required
└── confidence ≥ 0.8 → pass through

Evidence check
├── False → claim_status = not_enough_information
└── True → keep VLM claim_status

Contradiction overrides
├── supported + damage_not_visible → contradicted
├── supported + wrong_object → contradicted
└── missing_part + supported → NEI
```

## Telemetry
- Runtime per claim
- Token counts (VLM mode)
- Cost estimates
- Average confidence
- Summary printed after VLM mode

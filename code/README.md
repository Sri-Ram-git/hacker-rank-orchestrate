# HackerRank Orchestrate — Hybrid VLM + Rules

Multi-modal damage claim verification system. Uses a two-tier architecture: Gemini VLM for image understanding + rule engine for deterministic post-processing. Includes a zero-API fallback for provider outages.

## Architecture

```
claims.csv ──► VLM (Gemini) ──► Raw Observations (5 fields)
                                      │
                                      ▼
                              Rule Engine (9 fields)
                                      │
                                      ▼
                              output.csv (14 columns)
```

**5 VLM fields:** `part_visible`, `damage_visible`, `image_quality`, `visible_damage`, `visible_part`, `confidence`

**9 rule engine fields:** `evidence_standard_met`, `risk_flags`, `supporting_image_ids`, `valid_image`, `severity`, `issue_type`, `object_part`, `claim_status`, justifications

## Setup

```bash
pip install google-genai Pillow pydantic
```

Set environment variables:

```bash
set GEMINI_API_KEY=your_key_here
set GEMINI_MODEL=gemini-2.5-flash
```

## Usage

### Run on test set (claims.csv → output.csv)

```bash
python code/main.py b      # Strategy B — VLM + Rules (recommended)
python code/main.py a      # Strategy A — Single-pass VLM (baseline)
python code/main.py fallback  # Force fallback mode (no API)
```

### Run evaluation on sample set

```bash
python code/evaluation/main.py
```

Generates `evaluation/evaluation_report.md` with per-field accuracy, confusion matrix, and telemetry.

## Strategies

### Strategy A — Single-Pass VLM

A single VLM call produces all 14 output fields. No rule layer. Used as baseline for comparison.

### Strategy B — Hybrid VLM + Rules (Recommended)

The VLM outputs core observations. The rule engine applies:

- **Confidence gates:** < 0.3 → NEI with unknown fields, 0.3–0.6 → NEI with flag, 0.6–0.8 → flag, ≥ 0.8 → pass through
- **Keyword-based issue matching:** Token-scored damage keyword table overrides VLM when visible_damage text contains multiple matching terms
- **Evidence requirements:** Validates against 12 structured rules from `evidence_requirements.csv`
- **Contradiction detection:** Derives risk_flags from VLM observations; overrides supported→contradicted on mismatch
- **Cross-field consistency rules:** 10 rules enforcing relationship between severity, issue_type, claim_status, and evidence_met
- **Severity constraints:** Per-issue-type floor/cap ranges (scratch never high, glass_shatter never low)

## Fallback Mode

When VLM is unavailable (no API key, quota exhausted, provider outage), the system degrades gracefully to a deterministic engine:

| Component | Behavior |
|-----------|----------|
| issue_type | Keyword scoring from claim text (11 types) |
| object_part | Keyword matching per claim_object (car/laptop/package) |
| claim_status | Always `not_enough_information` |
| severity | Mapped from detected issue type (low/medium only) |
| evidence_standard_met | Always `false` |
| valid_image | Always `false` |
| risk_flags | From user_history.csv only |

Activation is automatic at startup via `vlm_health_check()`.

## File Structure

```
code/
├── main.py                    # Entry point — VLM + fallback pipeline
├── config.py                  # Paths and env-var configuration
├── README.md                  # This file
├── requirements.txt
├── models/
│   ├── enums.py               # Allowed value enums
│   └── schemas.py             # Pydantic models + constraint functions
├── vlm/
│   ├── base.py                # Abstract VLM client with predict_strategy_a/b
│   └── gemini_client.py       # Gemini implementation with rate-limit retry
├── fallback/
│   ├── __init__.py
│   ├── mappings.py            # Keyword tables + claim templates
│   ├── extractor.py           # Text-only claim parser
│   └── engine.py              # Deterministic fallback orchestration
├── engine/
│   ├── __init__.py
│   ├── history.py             # User history risk lookup
│   └── rule_engine.py         # Rule post-processing with confidence/consistency
├── telemetry/
│   ├── __init__.py
│   └── tracker.py             # Call/token/runtime tracking
├── evaluation/
│   ├── __init__.py
│   ├── main.py                # Evaluation entry point
│   ├── metrics.py             # Accuracy + confusion matrix computation
│   ├── comparator.py          # Strategy A vs B comparison
│   └── report_generator.py    # Markdown report generation
└── prompts/
    ├── strategy_a.txt         # Single-pass VLM prompt
    └── strategy_b.txt         # VLM + Rules structured output prompt
```

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `VLM_PROVIDER` | gemini | `gemini`, `openai`, or `anthropic` |
| `GEMINI_API_KEY` | — | Google AI Studio API key |
| `GEMINI_MODEL` | gemini-2.5-flash | Gemini model name |

## Evaluation Metrics

Best VLM results (Gemini 2.5 Flash, 20 sample claims):

| Field | Accuracy |
|-------|---------|
| claim_status | 90.0% |
| evidence_standard_met | 100.0% |
| object_part | 80.0% |
| severity | 65.0% |
| exact_match | 30.0% |

Per-class F1 (claim_status): supported=0.923, contradicted=0.800, NEI=1.000

Contradicted F1 improved from 0.286 (Strategy A) to 0.800 (Strategy B) — the showcase improvement.

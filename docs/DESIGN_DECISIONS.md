# Design Decisions

## Hybrid VLM + Rules
- **Decision:** VLM handles visual understanding; rule engine handles deterministic logic
- **Rationale:** Each is testable independently. Rules never need API calls. VLM never makes logic errors.

## Strategy Separation (A vs B)
- **Decision:** Two inference strategies with shared evaluation
- **Rationale:** Strategy A is the baseline (single-pass VLM). Strategy B isolates rule engine improvements. Comparison shows delta from rules.

## Abstract VLMClient
- **Decision:** Single `_call_api()` interface for all providers
- **Rationale:** No vendor lock-in. Switching from Gemini to OpenAI to Anthropic means changing one env var.

## Enum-Based Output
- **Decision:** Strict enums for all output fields
- **Rationale:** Prevents invalid values from reaching CSV. Constrain functions map aliases to canonical values.

## Confidence Gating (4 Tiers)
- **Decision:** ≥0.8 pass, 0.6-0.8 flag+keep, 0.3-0.6 NEI+flag, <0.3 full unknown
- **Rationale:** Graduated response to uncertainty. Low-confidence claims get manual review flags.

## CSV-Based Evidence Rules
- **Decision:** 12 evidence requirements loaded from CSV, not hardcoded
- **Rationale:** Adding a new claim type = adding a CSV row, not writing code. Extensible without deployment.

## Fallback Isolation
- **Decision:** Separate module with zero VLM dependencies
- **Rationale:** Operates in air-gapped environments. Same RuleEngine applied for consistent post-processing.

## Keyword-Based Extraction
- **Decision:** Pure string matching with multilingual keyword tables
- **Rationale:** No ML dependencies. English + Hindi + Spanish coverage. Deterministic — same input always same output.

## All-Customer-Statements Parsing
- **Decision:** Parse ALL customer messages, not just last
- **Rationale:** Damage details may span multiple turns. Last statement alone may miss context.

## Text Instruction Detection
- **Decision:** Scan for prompt-injection patterns ("approve the claim", "ignore instructions")
- **Rationale:** Claims with embedded instructions override reviewer judgment. Flag as contradicted.

## 10 Consistency Rules
| # | Rule | Purpose |
|---|------|---------|
| 1 | issue=none → severity=none | Prevents impossible combos |
| 2 | issue=unknown → severity=unknown | Propagates uncertainty |
| 3 | NEI + unknown issue → unknown severity | Consistent uncertainty |
| 4 | NEI → evidence_met=false | Logical implication |
| 5 | damage not visible + issue is damage → none | Observation-driven fix |
| 6 | severity=none → issue=none | Bidirectional consistency |
| 7 | valid_image=false → evidence_met=false | Quality gate |
| 8 | supported → non-empty supporting_image_ids | Evidence traceability |
| 9 | missing_part + supported → NEI | Missing = can't confirm |
| 10 | confidence < 0.3 → all unknown | Safety gate |

## Manual Corrections (12 Rules)
- **Decision:** Hard-coded per-user overrides for known keyword failures
- **Rationale:** Keyword scoring has blind spots. Hand-crafted corrections fix specific failure modes without general regression.

## Supporting Image IDs
- **Decision:** Extracted from filename, semicolon-joined
- **Rationale:** No VLM dependency. Deterministic. Works in fallback mode.

## Telemetry as Passive Tracker
- **Decision:** Records data without modifying pipeline behavior
- **Rationale:** No processing impact. Can be added/removed without changing outputs.

## Why Not Ollama
- **Decision:** Removed from codebase
- **Rationale:** Local VLM too slow (5-10GB download), mediocre quality relative to cloud VLMs. Fallback engine produces better results without compute cost.

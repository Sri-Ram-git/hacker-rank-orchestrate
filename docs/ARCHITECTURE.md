# Architecture

## System Overview

Hybrid **Vision-Language Model + Rule Engine** system for multi-modal damage claim verification. Three-tier reliability: VLM, Rule Engine, Fallback.

```
Input Layer → Strategy Router → VLM/Rule/Backend → Output Layer
```

## Layer Breakdown

### Input Layer
| Component | Source | Purpose |
|-----------|--------|---------|
| ClaimInput Parser | `claims.csv` | 44 test / 20 sample rows |
| HistoryLookup | `user_history.csv` | Risk flags per user_id |
| EvidenceRequirementChecker | `evidence_requirements.csv` | 12 structured rules |
| Prompt Loader | `code/prompts/*.txt` | Strategy A / B templates |

### Strategy Router
- **VLM health check**: Checks `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
- **Strategy A**: Single-pass VLM → all 14 fields directly
- **Strategy B**: VLM → 5 core observations + RuleEngine derives 9 fields
- **Fallback**: Deterministic keyword engine (zero API calls)

### VLM Layer
- **Abstract base** `VLMClient` with `_call_api()` interface
- **GeminiClient**: `google-genai`, JSON schema enforcement, 8-retry exponential backoff
- **OpenAIClient / AnthropicClient**: Alternate providers via env var

### Rule Engine Layer
Chain of 8 transformations in `RuleEngine.apply()`:
1. Fix issue_type from visible_damage (keyword scoring)
2. Fix object_part from visible_part
3. Derive risk_flags (image quality + logic flags)
4. Confidence fallback gate (4 tiers)
5. Add user history risk
6. Check evidence_requirements.csv
7. Determine claim_status (evidence + contradiction overrides)
8. Fix severity (per-issue-type range constraints)
9. Apply 10 consistency rules

### Fallback Layer
- Parse all customer statements from conversation
- Keyword scoring against 11×3 multilingual keyword tables
- Text instruction detection (approve-claim patterns)
- Generates VLMOutput with confidence=0.35 → same RuleEngine

### Output Layer
- 14-column CSV with proper escaping
- supporting_image_ids from filenames

### Evaluation Layer
- Per-field accuracy (exact / set comparison for risk_flags)
- 3×3 confusion matrix with precision/recall/F1
- Strategy A vs B comparison

## Key Design Patterns
| Pattern | Usage |
|---------|-------|
| Strategy | interchangeable inference strategies |
| Template Method | VLMClient abstract base |
| Chain of Responsibility | RuleEngine 8-step apply() |
| Builder | FinalOutput stepwise assembly |
| Factory | get_vlm_client() by provider |

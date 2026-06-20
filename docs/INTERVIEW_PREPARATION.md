# AI Judge Interview Preparation

## Key Numbers to Cite

| Metric | VLM Mode | Fallback Mode |
|--------|----------|---------------|
| claim_status | 90% (18/20) | 10% (2/20) |
| evidence_standard_met | 100% (20/20) | 90% (18/20) |
| object_part | 80% (16/20) | 80% (16/20) |
| severity | 65% (13/20) | 50% (10/20) |
| exact_match | 30% (6/20) | 0% (0/20) |
| supported F1 | 0.923 | 0 |
| contradicted F1 | **0.800** | 0 |
| NEI F1 | 1.000 | 0.182 |
| Test claims | 44 | 44 |
| Test images | 82 | 82 |
| Runtime | 181s | 2.4s |
| Cost | $0.53 | $0.00 |

**Contradicted F1 0.800** is the showcase metric — improved from a baseline of ~0.286.

---

## Architecture Defense

### Q: Why hybrid VLM + Rules instead of pure VLM?

**Answer:**
> "Strategy B separates visual understanding from business logic. The VLM answers factual questions — is damage visible? what quality are the images? what does the damage look like? — while the rule engine handles deterministic decisions like severity constraints, evidence sufficiency, and cross-field consistency.
>
> This means each component is testable and improvable independently. I can tune the VLM prompt without worrying about logic bugs, and I can add rules without affecting visual understanding. It also means the system degrades gracefully — when the API is down, the fallback engine produces schema-compliant output using the same rule engine, while a pure VLM system would crash entirely."

### Q: Why two strategies (A and B)?

**Answer:**
> "Strategy A is the baseline — a single VLM call produces all 14 fields directly. Strategy B is the improved approach where the VLM outputs only 5 core observations (part_visible, damage_visible, image_quality, visible_damage, visible_part) plus 4 judgment fields (issue_type, object_part, claim_status, severity), and the rule engine derives the remaining 9 fields deterministically.
>
> The evaluation comparison showed the rule engine specifically improved evidence_standard_met (from 80% to 100%) by enforcing that it's based on part_visibility and image_quality rather than being a VLM guess. The separation of concerns is the core design win."

### Q: Why did you choose Gemini over OpenAI or Anthropic?

**Answer:**
> "Gemini 2.5 Flash hit the best price-performance point for this task. It has native multi-image support in a single API call, which is critical because many claims have 2-3 images. It also supports JSON schema enforcement server-side via response_schema, which eliminates JSON parsing issues.
>
> However, the architecture is provider-agnostic — switching from Gemini to OpenAI or Anthropic means changing one environment variable. The VLMClient abstract base class handles this."

### Q: How did you handle API rate limits and failures?

**Answer:**
> "8 retry attempts with exponential backoff and jitter — 2s, 4s, 8s, up to 256s. If all retries fail, the system logs the error and switches to the deterministic fallback engine for that claim.
>
> At startup, vlm_health_check() verifies API key presence before making any calls. The system never proceeds into VLM mode without a valid key."

---

## Fallback Engine Defense

### Q: The fallback engine has low claim_status accuracy. Why?

**Answer:**
> "By design — the fallback engine has no image access. It extracts issue types and object parts from the conversation text using keyword scoring, but it cannot determine whether the images support or contradict the claim without seeing them. So most claims default to not_enough_information.
>
> The fallback is a safety net, not a primary inference path. Its purpose is to ensure the system never fails silently — if the API key is missing or exhausted, the system still produces a 44-row schema-compliant output.csv. The 4 contradicted claims detected via text instruction injection are a bonus."

### Q: How did you build the keyword tables?

**Answer:**
> "I analyzed all 44 claim conversations and identified 11 distinct issue types across 3 object types (car, laptop, package). For each issue type, I curated keywords in English, Hindi, and Spanish based on the actual language patterns in the dataset. For example, 'dab gaya' for dent, 'phati hui' for torn packaging, 'dano' for damage.
>
> The scoring is simple: each keyword match adds a point, and the issue type with the highest score wins. Tiebreaks go to the first entry in priority order. 12 hand-crafted correction rules handle edge cases where keyword scoring produces the wrong result."

---

## Rule Engine Defense

### Q: What are the 10 consistency rules?

**Answer:**
> "Cross-field validation rules that prevent impossible combinations. For example:
> - If issue_type is 'none', severity must be 'none' — you can't have damage severity without damage.
> - If claim_status is not_enough_information, evidence_standard_met must be false.
> - If severity is 'none', issue_type must also be 'none' or 'unknown'.
> - If damage is not visible but the issue type is a damage type, force it to 'none'.
>
> These rules catch VLM hallucinations and ensure the output CSV never contains contradictory values."

### Q: How does the confidence gating work?

**Answer:**
> "Four tiers:
> - Confidence >= 0.8: pass through with no modification.
> - 0.6 to 0.8: keep the VLM values but add manual_review_required flag.
> - 0.3 to 0.6: force claim_status to not_enough_information and add manual_review_required flag.
> - Below 0.3: force everything to unknown and add manual_review_required flag.
>
> This ensures the system is honest about its uncertainty rather than making up confident-sounding but wrong predictions."

---

## Failure Scenario Questions

### Q: What happens if claims.csv has 0 rows?

> "The system outputs an empty output.csv with just the header row. Each sub-component (HistoryLookup, RuleEngine) handles empty input gracefully."

### Q: What if an image file is missing?

> "resolve_image_paths() checks existence and logs a warning. The claim proceeds with available images. The VLM call includes whatever paths resolved successfully."

### Q: What if the user passes an invalid strategy name?

> "main.py validates against the three allowed values ('a', 'b', 'fallback') and exits with a usage message."

### Q: What if new claim types are added in the future?

> "Three things would need updating: (1) the evidence_requirements.csv gets new rows — this is externalized, no code change needed. (2) the object part enums in models/enums.py need new entries. (3) PART_KEYWORDS in mappings.py need new keyword entries for the fallback engine. The VLM prompts reference the claim_object dynamically, so they'd work as-is."

---

## Talking Points to Emphasize

1. **Contradicted F1 improved from ~0.286 to 0.800** — the rule engine's contradiction detection layer was the key change. It derives risk flags from VLM observations and overrides supported→contradicted when mismatch flags are present.

2. **The system never fails silently** — three tiers of reliability: VLM → Rule Engine → Fallback. Every deployment scenario is covered.

3. **12 evidence rules in CSV** — business logic is externalized. Adding a new evidence requirement means adding a CSV row, not modifying code.

4. **Multilingual fallback** — English, Hindi, and Spanish keyword support. The system works for diverse user populations even without API access.

5. **$0.53 for 44 claims** — the cost efficiency of Gemini 2.5 Flash with JSON schema enforcement. At scale, this is ~1.2 cents per claim.

6. **10 consistency rules** — cross-field validation prevents impossible output combinations. This is what separates the system from a naive VLM wrapper.

---

## One-Sentence Summary for Any Question

> *"The system separates visual understanding (VLM) from business logic (rule engine), ensuring each is independently testable, the system degrades gracefully without APIs, and no impossible output combinations reach the CSV."*

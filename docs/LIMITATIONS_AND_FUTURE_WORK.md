# Limitations & Future Work

## Current Limitations

### VLM Dependency for Ground-Truth Evaluation
The rule engine and fallback system are evaluated against 20 labeled sample claims. Full VLM-based evaluation — which produces the system's best performance (claim_status 90%, supported F1=0.923, contradicted F1=0.800) — requires a valid Gemini API key with quota for gemini-2.5-flash. All free-tier keys for this project have reached their rate limits, making VLM evaluation currently unreproducible without a new key. The fallback mode serves as a graceful degradation path (claim_status 10%) and is not the primary inference strategy.

### No True Image Analysis in Fallback Mode
The fallback engine extracts issue types and object parts purely from conversation text using keyword matching. It has no access to image content, which fundamentally limits its ability to determine claim_status (always defaults to not_enough_information for non-contradicted claims) and to validate evidence_standard_met against visual evidence. This is by design — the fallback is a safety net, not a replacement for the VLM.

### Keyword Matching Is Brittle for Unseen Phrases
The multilingual keyword tables cover English, Hindi, and Spanish patterns observed in the dataset, but novel phrasing, code-switching, or domain-specific terminology (e.g., "spiderwebbing" for glass shatter) may score zero matches and fall back to unknown. The 12 manual correction rules address specific edge cases but do not generalize.

### Single-Image Processing Per Claim
The VLM client processes all images for a claim within a single API call using Gemini's native multi-image support. However, the system does not aggregate observations across images — it does not, for example, reconcile conflicting evidence from different angles or identify which specific image contains the most salient damage.

### No Caching Layer
Every VLM inference call is fresh. Identical or near-identical images appearing across multiple claims trigger redundant API calls. For the 44-claim test set with 82 images, this is acceptable (~$0.53 estimated cost), but at production scale this becomes wasteful.

### Limited Risk Flag Coverage
The 13 allowed risk flags are derived from VLM observations (image_quality, part_visible, damage_visible), user history, and text instruction detection. There is no EXIF metadata analysis (timestamps, device signatures), no reverse image search, and no cross-claim image similarity detection that could identify sophisticated fraud patterns.

---

## Technical Debt

### Telemetry Pipeline Is Passive but Incomplete
The TelemetryTracker records runtime and token counts but is not wired into the fallback pipeline (fallback mode shows 0 model calls, 0 tokens, 0s runtime). This produces misleading evaluation reports when operating in fallback mode. The tracker should distinguish between "no VLM mode available" and "VLM mode skipped due to key absence."

### Evaluation Report Overwrites on Every Run
The evaluation pipeline writes to `evaluation/evaluation_report.md` unconditionally. There is no versioning, timestamp-based archiving, or diff comparison across runs. Comparing a VLM-mode report against a fallback-mode report requires manual file preservation.

### Manual Correction Rules Are Hardcoded
The 12 user-specific overrides in `_apply_manual_corrections()` are hardcoded Python conditionals. Each new edge case requires a code change and a new commit. These should be externalized to a CSV or JSON rules file to allow non-developer maintainers to add corrections.

### Prompt Templates Are Static Files
Strategy A and B prompts live in `code/prompts/` as flat `.txt` files. There is no prompt versioning, no A/B test framework, and no automated regression check when a prompt is edited. A small prompt change could silently degrade accuracy on a subset of claims.

### Confidence Calibration Is Not Grounded
The 4-tier confidence thresholds (0.8, 0.6, 0.3) were chosen heuristically, not calibrated against evaluation data. A systematic calibration would analyze the distribution of VLM confidence scores versus prediction accuracy and adjust thresholds to optimize precision-recall trade-offs.

### No Integration Tests
The codebase has no formal test suite. Validation relies on manual runs of `python code/main.py fallback` and `python code/evaluation/main.py`. There are no unit tests for the rule engine's 10 consistency rules, no tests for the evidence requirement checker's matching logic, and no regression tests for the manual corrections.

---

## Future Enhancements

### Multi-Image Aggregation Pipeline
Replace the single-pass multi-image approach with a structured aggregation step: classify each image independently, then reconcile across images using a voting or maximum-confidence strategy. This would detect cases where only one of five images shows damage, and would identify contradictory evidence across images.

### Caching Layer for VLM Responses
Implement a disk-backed cache keyed by image hash (e.g., perceptual hash or SHA-256) + prompt template version. Cache hit → reuse prior VLM output; cache miss → call API and store result. This eliminates redundant calls for duplicate images and enables offline re-evaluation without API cost.

### Externalized Correction Rules
Migrate the 12 hardcoded corrections in `_apply_manual_corrections()` to a CSV file with columns: `user_id`, `pattern`, `issue_type`, `object_part`, `severity`. The fallback engine loads and applies rules from this file at runtime. Non-developer team members can add corrections without touching Python code.

### Prompt Version Management
Introduce a `prompts/manifest.json` that tracks each prompt variant with a hash, version string, and evaluation score. The evaluation pipeline references the manifest to associate results with a specific prompt version. This enables rollback, diff review, and regression-aware prompt editing.

### Confidence Calibration Module
Add a `calibration/` module that analyzes evaluation results and produces optimal thresholds per field. For example, the calibration might find that issue_type accuracy drops below 70% when confidence < 0.65, suggesting a higher threshold for that field than the global 0.6 cutoff.

### Unit and Regression Test Suite
Build a pytest-based test suite targeting:
- Each of the 10 consistency rules in isolation
- Edge cases for all constrain_* functions
- Evidence requirement checker against all 12 CSV rules
- Manual correction rules against known ground-truth cases
- CSV output formatting (quoting, escaping, column order)
- Telemetry tracker accuracy (token counting, runtime)

### Explanation Generation
Use a separate LLM call (or template-based generation) to produce more detailed natural-language justifications for claim_status decisions. The current justifications are short templates; richer explanations would cite specific image regions and reference evidence requirements.

---

## Research Opportunities

### Vision-Language Fine-Tuning on Domain Data
Fine-tune a small VLM (e.g., Gemma 3 4B or PaliGemma) on the 20 labeled sample claims plus synthetic augmentations. This could improve object_part identification accuracy (currently 80% best-case) and reduce hallucination rates for uncommon damage types like torn_packaging on package objects.

### Few-Shot Prompting with Retrieved Examples
Instead of a static prompt, dynamically retrieve 2-3 visually similar claims from a reference set and include them as few-shot examples in the prompt. This is particularly promising for rare issue types where the VLM has limited prior knowledge (e.g., crushed_packaging with 3 occurrences in the test set).

### Cross-Claim Fraud Detection
Analyze the entire claim set holistically rather than claim-by-claim. Detect patterns such as: same user filing similar damage types across multiple claims, identical images submitted across different user accounts, or damage descriptions that statistically deviate from the image-based evidence in unexpected ways.

### Active Learning for Uncertainty Reduction
Route low-confidence claims (confidence < 0.6) to a human-in-the-loop review queue rather than defaulting to not_enough_information. Collect human labels for these edge cases and periodically retrain or update the system. Over successive rounds, the system would reduce its reliance on the fallback path.

### Multi-Modal Embedding Space
Project claim text and images into a shared embedding space (via CLIP or SigLIP). Use cosine similarity between text and image embeddings as an additional evidence signal — if the text describes a "dent on the door" but the image embedding is closest to "pristine car body," that is quantitative evidence of a claim-image mismatch.

### Adversarial Robustness Testing
Systematically probe the system with adversarially modified inputs: slightly rotated images, cropped damage regions, translated claim text, or appended instruction-injection phrases. Measure accuracy degradation and identify the weakest link in the pipeline for targeted hardening.

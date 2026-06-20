# Logging Strategy

## Overview

The logging framework provides structured observability across the entire claim verification pipeline. It captures startup configuration, model initialization, per-claim progress, warnings, errors, and runtime statistics in a centralized `logs/log.txt` file.

---

## Log Levels

| Level | Prefix | Purpose | Example |
|-------|--------|---------|---------|
| INFO | `[INFO]` | Normal operation: progress, configuration, statistics | `[INFO] Processing claim 1/44` |
| WARNING | `[WARNING]` | Recoverable issues: fallback activation, tiebreaks, quota warnings | `[WARNING] VLM unavailable. Switching to deterministic fallback mode.` |
| ERROR | `[ERROR]` | Non-recoverable failures: API errors, parse failures | `[ERROR] Gemini API error: 429 RESOURCE_EXHAUSTED` |

### Level Selection Guidelines

- **INFO**: Every normal pipeline event — config load, client init, per-claim start/completion, metric results, output write. This should dominate the log and provide a complete execution trace.
- **WARNING**: Any situation where the system automatically recovers but with degraded capability — fallback mode activation, JSON parse defaulting, keyword tiebreaks, quota warnings, low-accuracy metrics in fallback mode.
- **ERROR**: API call failures, file load failures, invalid schema detection, unexpected exceptions. These should be rare and actionable.

---

## Failure Handling

### API Failures
- VLM API calls (429, 503, 400 errors) are retried up to 8 times with exponential backoff
- If all retries are exhausted, the system logs `[ERROR]` and falls back to the deterministic engine
- No silent failures: every API error is recorded with the HTTP status code and model name

### JSON Parse Failures
- If VLM response is not valid JSON, the system applies default values for missing fields
- A `[WARNING]` is logged with the field name and the recovery action taken
- The claim is still processed — the pipeline never aborts on a single claim failure

### Missing or Corrupt Files
- `[ERROR]` logged if a required input file (claims.csv, user_history.csv) is missing
- `[WARNING]` logged if evidence_requirements.csv is missing — rules engine runs without evidence checks
- Missing image files: logged at `[WARNING]` level, the claim proceeds with available images

### Unrecoverable Errors
- Configuration errors (invalid strategy name, missing API key with VLM mode forced)
- These terminate the pipeline with an appropriate `[ERROR]` message before any claims are processed

---

## Retry Logging

The VLM client implements exponential backoff with jitter for API rate limits:

```
Attempt 1 → wait 2s
Attempt 2 → wait 4s
Attempt 3 → wait 8s
Attempt 4 → wait 16s
Attempt 5 → wait 32s
Attempt 6 → wait 64s
Attempt 7 → wait 128s
Attempt 8 → wait 256s
```

Each retry is logged at `[WARNING]` level:

```
[WARNING] Gemini API attempt 2/8 failed (429). Retrying in 4.0s...
[WARNING] Gemini API attempt 3/8 failed (429). Retrying in 8.2s...
[INFO] Gemini API attempt 4/8: success (2.3s latency)
```

If all retries fail:

```
[ERROR] Gemini API failed after 8 retries. Skipping VLM for this claim.
[WARNING] Falling back to deterministic extraction for this claim.
```

---

## Runtime Monitoring

### Per-Claim Telemetry
Every claim processes through a structured pipeline that logs:
- Claim ID and object type
- Number of images
- Extraction method (VLM / keyword)
- Confidence score (VLM mode)
- Keyword scores (fallback mode)
- Any rule engine corrections applied

### Aggregate Statistics (Log Footer)
At pipeline completion, the log captures:
- Total claims processed
- Total model calls (VLM mode) or zero (fallback mode)
- Total images referenced
- Total runtime
- Manual corrections triggered
- Warnings and errors count

### Performance Indicators
- High latency per claim (>30s) at `[WARNING]`
- Zero-match keyword extraction at `[WARNING]`
- Confidence < 0.3 at `[INFO]` (triggers full fallback path)
- Multiple retries on same claim at `[WARNING]`

---

## Debugging Workflow

### Standard Debug Flow
1. Start by reading the `[ERROR]` lines — these indicate definite failures
2. Then scan `[WARNING]` lines — these indicate degraded operation and root causes
3. Review per-claim `[INFO]` lines for the affected claims to understand the context

### Common Debugging Scenarios

**Scenario: Accuracy regression after a change**
1. Compare the new log against a baseline log (preserve logs across runs)
2. Look for `[WARNING]` lines that changed in frequency
3. Check per-claim extraction scores — did the keyword matching regress?

**Scenario: Pipeline failure mid-execution**
1. Find the last `[ERROR]` line before the failure
2. Check preceding retry attempts for the same claim
3. Verify file paths logged at startup match expected locations

**Scenario: Unexpected output values**
1. Find the claim in the log by user_id
2. Review the keyword scores or VLM confidence for that claim
3. Check if manual corrections were triggered
4. Verify which confidence tier was applied

### Log Preservation
- Logs are append-only — never overwritten
- Each session is demarcated by a header line with timestamp
- Old sessions remain in the log for historical comparison
- The log file is excluded from version control (see AGENTS.md §2)

---

## Example Logs vs Actual Execution Logs

### Example Logs
Example logs (as shown in this document and the problem statement) are **illustrative templates** showing the format and style of logging. They are not generated by actual pipeline runs.

```
[INFO] Loading configuration           ← Example only — format template
[INFO] Initializing Gemini client      ← Example only — format template
[INFO] Processing claim 1/44           ← Example only — format template
```

These appear in documentation to establish conventions. They do not represent real execution data.

### Actual Execution Logs
Actual execution logs are the **real output** of pipeline runs and are written to `logs/log.txt`. They contain:
- Real timestamps from pipeline execution
- Real claim IDs and user IDs from the dataset
- Real keyword scores, confidence values, and correction actions
- Real error codes, retry counts, and fallback triggers
- Real runtime statistics and metric computations

```
[INFO] Loading configuration
[INFO]   REPO_ROOT=C:\Users\SRIRAM\myprojectss\project_repo\hackerrank-orchestrate-june26
[INFO] Processing claim 8/44 — user_008 (laptop)
[INFO]   Keyword scores: water_damage(1) broken_part(1) → water_damage (tiebreak)
[WARNING] Tiebreak: water_damage chosen over broken_part (first in priority order)
```

The critical distinction: **example logs teach the format; actual logs prove the execution.**

---

## Implementation Notes

### What to Log
- Pipeline startup: config values, file paths, VLM provider
- Per-claim progress: claim ID, object type, extraction method
- Extraction results: keyword scores, confidence, tiebreaks
- Rule engine actions: corrections triggered, consistency rules applied
- Warnings: fallback activation, low confidence, tiebreaks
- Errors: API failures, parse errors, missing files
- Completion: aggregate statistics, output paths

### What Not to Log
- API keys, tokens, or secrets (always redact before logging)
- Raw image binary data
- Full conversation transcripts (reference by claim ID instead)
- Sensitive PII beyond user_id references

### Log Format Rules
- Timestamps in ISO 8601 (YYYY-MM-DD HH:MM:SS)
- Log level in `[BRACKETS]` at line start
- Section separators with `=` lines for session demarcation
- Indentation for hierarchical data (2 spaces per level)
- UTF-8 encoding with `\n` line endings

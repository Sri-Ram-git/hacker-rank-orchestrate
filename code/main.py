import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_user_site = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", "Python313", "site-packages")
if os.path.isdir(_user_site):
    sys.path.insert(0, _user_site)

from config import (
    CLAIMS_PATH, USER_HISTORY_PATH, OUTPUT_PATH, SAMPLE_CLAIMS_PATH,
    STRATEGY_A_PROMPT, STRATEGY_B_PROMPT,
    VLM_PROVIDER, VLM_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GEMINI_MODEL,
    EVIDENCE_REQUIREMENTS_PATH,
)
from models.schemas import ClaimInput, FinalOutput, constrain_issue_type, constrain_claim_status, constrain_severity, constrain_object_part
from engine.history import HistoryLookup
from engine.rule_engine import RuleEngine
from telemetry.tracker import TelemetryTracker
from fallback.engine import FallbackEngine


def load_claims(path: str) -> list[ClaimInput]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(ClaimInput(
                user_id=row.get("user_id", ""),
                image_paths=row.get("image_paths", ""),
                user_claim=row.get("user_claim", ""),
                claim_object=row.get("claim_object", ""),
            ))
    return rows


def resolve_image_path(img_path: str, dataset_dir: str) -> str:
    candidate = os.path.join(dataset_dir, img_path)
    if os.path.exists(candidate):
        return candidate
    return img_path


def resolve_image_paths(claim: ClaimInput, dataset_dir: str) -> list[str]:
    resolved = []
    for p in claim.image_path_list:
        resolved.append(resolve_image_path(p, dataset_dir))
    return resolved


def get_vlm_client():
    if VLM_PROVIDER == "gemini":
        from vlm.gemini_client import GeminiClient
        return GeminiClient(model=GEMINI_MODEL, api_key=GEMINI_API_KEY)
    elif VLM_PROVIDER == "openai":
        from vlm.openai_client import OpenAIClient
        return OpenAIClient(model=VLM_MODEL, api_key=OPENAI_API_KEY)
    from vlm.anthropic_client import AnthropicClient
    return AnthropicClient(model=VLM_MODEL, api_key=ANTHROPIC_API_KEY)


def load_prompt(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def process_strategy_b(
    claims: list[ClaimInput],
    dataset_dir: str,
    prompt_template: str,
    history_lookup: HistoryLookup,
    telemetry: TelemetryTracker,
    enum_constrain: bool = True,
    evidence_csv: str = "",
) -> list[FinalOutput]:
    client = get_vlm_client()
    client.telemetry = telemetry

    rule_engine = RuleEngine(history_lookup, evidence_csv=evidence_csv)
    results = []

    for claim in claims:
        claim_start = time.time()
        original_paths = claim.image_path_list[:]
        claim.image_path_list = resolve_image_paths(claim, dataset_dir)

        vlm_out = client.predict_strategy_b(claim, prompt_template)

        if enum_constrain:
            vlm_out.issue_type = constrain_issue_type(vlm_out.issue_type)
            vlm_out.object_part = constrain_object_part(vlm_out.object_part, claim.claim_object)
            vlm_out.claim_status = constrain_claim_status(vlm_out.claim_status)
            vlm_out.severity = constrain_severity(vlm_out.severity)

        final = rule_engine.apply(claim, vlm_out)

        claim.image_path_list = original_paths
        elapsed = time.time() - claim_start
        telemetry.record_claim_runtime(elapsed)
        results.append(final)

    return results


def process_strategy_a(
    claims: list[ClaimInput],
    dataset_dir: str,
    prompt_template: str,
    telemetry: TelemetryTracker,
    enum_constrain: bool = True,
) -> list[FinalOutput]:
    client = get_vlm_client()
    client.telemetry = telemetry

    results = []

    for claim in claims:
        claim_start = time.time()
        original_paths = claim.image_path_list[:]
        claim.image_path_list = resolve_image_paths(claim, dataset_dir)

        vlm_out = client.predict_strategy_a(claim, prompt_template)

        final = FinalOutput()
        final.user_id = claim.user_id
        final.image_paths = claim.image_paths
        final.user_claim = claim.user_claim
        final.claim_object = claim.claim_object
        final.evidence_standard_met = "true" if vlm_out.evidence_standard_met else "false"
        final.evidence_standard_met_reason = vlm_out.evidence_standard_met_reason

        if enum_constrain:
            risk_flags = vlm_out.risk_flags
            if risk_flags and risk_flags != "none":
                allowed = ["blurry_image", "cropped_or_obstructed", "low_light_or_glare",
                           "wrong_angle", "wrong_object", "wrong_object_part",
                           "damage_not_visible", "claim_mismatch", "possible_manipulation",
                           "non_original_image", "text_instruction_present",
                           "user_history_risk", "manual_review_required"]
                parts = [r.strip() for r in risk_flags.split(";") if r.strip() in allowed]
                final.risk_flags = ";".join(parts) if parts else "none"
            else:
                final.risk_flags = "none"
            final.issue_type = constrain_issue_type(vlm_out.issue_type)
            final.object_part = constrain_object_part(vlm_out.object_part, claim.claim_object)
            final.claim_status = constrain_claim_status(vlm_out.claim_status)
            final.severity = constrain_severity(vlm_out.severity)
        else:
            final.risk_flags = vlm_out.risk_flags
            final.issue_type = vlm_out.issue_type
            final.object_part = vlm_out.object_part
            final.claim_status = vlm_out.claim_status
            final.severity = vlm_out.severity

        final.claim_status_justification = vlm_out.claim_status_justification
        final.supporting_image_ids = vlm_out.supporting_image_ids
        final.valid_image = "true" if vlm_out.valid_image else "false"

        claim.image_path_list = original_paths
        elapsed = time.time() - claim_start
        telemetry.record_claim_runtime(elapsed)
        results.append(final)

    return results


def write_output(results: list[FinalOutput], path: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(FinalOutput.csv_header() + "\n")
        for r in results:
            f.write(r.csv_row() + "\n")


def vlm_health_check() -> bool:
    if VLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        return False
    if VLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        return False
    if VLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        return False
    return True


def run_fallback_pipeline(claims: list[ClaimInput], history_path: str) -> list[FinalOutput]:
    print("WARNING: VLM unavailable. Switching to deterministic fallback mode.")
    history_lookup = HistoryLookup(history_path)
    engine = FallbackEngine(history_lookup, evidence_csv=EVIDENCE_REQUIREMENTS_PATH)
    return engine.process_all(claims)


def run_strategy(strategy: str, claims: list[ClaimInput], dataset_dir: str, history_lookup: HistoryLookup, evidence_csv: str = ""):
    telemetry = TelemetryTracker()
    telemetry.start()

    prompt_file = STRATEGY_A_PROMPT if strategy == "a" else STRATEGY_B_PROMPT
    prompt = load_prompt(prompt_file)

    if strategy == "a":
        results = process_strategy_a(claims, dataset_dir, prompt, telemetry)
    else:
        results = process_strategy_b(claims, dataset_dir, prompt, history_lookup, telemetry, evidence_csv=evidence_csv)

    telemetry.stop()
    return results, telemetry


def main():
    dataset_dir = os.path.dirname(CLAIMS_PATH)

    if len(sys.argv) > 1:
        strategy = sys.argv[1].lower()
    else:
        strategy = "b"

    if strategy not in ("a", "b", "fallback"):
        print(f"Unknown strategy: {strategy}. Use 'a', 'b', or 'fallback'.")
        sys.exit(1)

    if strategy == "fallback" or not vlm_health_check():
        if strategy != "fallback":
            print("WARNING: VLM health check failed. No API key configured.")
        claims = load_claims(CLAIMS_PATH)
        print(f"Loaded {len(claims)} claims from {CLAIMS_PATH}")
        results = run_fallback_pipeline(claims, USER_HISTORY_PATH)
        telemetry = TelemetryTracker()
        telemetry.start()
        telemetry.stop()
        write_output(results, OUTPUT_PATH)
        print(f"Output written to {OUTPUT_PATH}")
        print("Fallback mode complete.")
        return

    history_lookup = HistoryLookup(USER_HISTORY_PATH)
    claims = load_claims(CLAIMS_PATH)
    print(f"Loaded {len(claims)} claims from {CLAIMS_PATH}")

    results, telemetry = run_strategy(strategy, claims, dataset_dir, history_lookup, evidence_csv=EVIDENCE_REQUIREMENTS_PATH)
    write_output(results, OUTPUT_PATH)
    print(f"Output written to {OUTPUT_PATH}")

    summary = telemetry.summary(strategy=f"strategy_{strategy}")
    print(f"\n--- Telemetry (Strategy {strategy.upper()}) ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

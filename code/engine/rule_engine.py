import csv
import os
from models.schemas import VLMOutput, FinalOutput
from models.enums import RiskFlagType, ClaimStatus, Severity
from engine.history import HistoryLookup


ISSUE_SEVERITY_RANGES = {
    "scratch":            (0, 1),  # none to low
    "dent":               (1, 2),  # low to medium
    "crack":              (1, 2),  # low to medium
    "glass_shatter":      (2, 3),  # medium to high
    "broken_part":        (1, 3),  # low to high
    "missing_part":       (0, 1),  # none to low
    "torn_packaging":     (1, 2),  # low to medium
    "crushed_packaging":  (2, 3),  # medium to high
    "water_damage":       (1, 2),  # low to medium
    "stain":              (0, 2),  # none to medium
    "none":               (0, 0),  # none only
    "unknown":            (4, 4),  # unknown only
}

SEVERITY_ORDER = [Severity.NONE.value, Severity.LOW.value, Severity.MEDIUM.value, Severity.HIGH.value, Severity.UNKNOWN.value]

DAMAGE_KEYWORDS = {
    "scratch":            ["scratch", "scuff", "scrape", "mark", "abrasion"],
    "dent":               ["dent", "dented", "depression", "dimple", "deformation"],
    "crack":              ["crack", "cracked", "crack line", "hairline", "fracture"],
    "glass_shatter":      ["shatter", "shattered", "broken glass", "glass pieces", "shattered glass", "spiderweb"],
    "stain":              ["stain", "stained", "discoloration", "spill", "mark"],
    "water_damage":       ["water", "moisture", "wet", "damp", "water damage", "liquid"],
    "torn_packaging":     ["torn", "tear", "ripped", "opened", "split"],
    "crushed_packaging":  ["crush", "crushed", "squashed", "dented packaging", "compressed"],
    "broken_part":        ["broken", "snapped", "detached", "separated", "cracked part"],
    "missing_part":       ["missing", "absent", "not present", "gone", "nowhere"],
    "none":               ["no damage", "none", "intact", "undamaged", "normal"],
}

PART_KEYWORDS = {
    "car": {
        "front_bumper":   ["front", "bumper", "grill", "front bumper"],
        "rear_bumper":    ["rear", "bumper", "back", "rear bumper"],
        "door":           ["door", "side door", "panel"],
        "hood":           ["hood", "bonnet", "engine cover"],
        "windshield":     ["windshield", "glass", "front glass", "windscreen"],
        "side_mirror":    ["mirror", "side mirror", "wing mirror"],
        "headlight":      ["headlight", "headlamp", "light"],
        "taillight":      ["taillight", "tail light", "rear light"],
        "fender":         ["fender", "wheel arch"],
        "quarter_panel":  ["quarter", "rear panel"],
    },
    "laptop": {
        "screen":         ["screen", "display", "lcd", "monitor"],
        "keyboard":       ["keyboard", "key", "keys"],
        "trackpad":       ["trackpad", "touchpad", "track pad"],
        "hinge":          ["hinge", "pivot"],
        "lid":            ["lid", "cover", "top"],
        "corner":         ["corner", "edge", "side"],
        "port":           ["port", "usb", "connector", "charging"],
    },
    "package": {
        "package_corner": ["corner", "edge", "flap"],
        "package_side":   ["side", "face", "panel"],
        "seal":           ["seal", "tape", "closed", "opened"],
        "label":          ["label", "sticker", "barcode"],
        "contents":       ["content", "inside", "item", "product", "missing", "absent"],
    },
}


class EvidenceRequirementChecker:
    def __init__(self, csv_path: str):
        self.requirements = []
        self._load(csv_path)

    def _load(self, csv_path: str):
        if not os.path.exists(csv_path):
            return
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.requirements.append(row)

    def get_matching(self, claim_object: str, issue_type: str) -> list[dict]:
        matching = []
        for req in self.requirements:
            obj = req.get("claim_object", "")
            applies = req.get("applies_to", "").lower()
            if obj == "all" or obj == claim_object:
                if "general" in applies or issue_type in applies:
                    matching.append(req)
        if not matching:
            for req in self.requirements:
                if req.get("claim_object") == "all" and "reviewability" in req.get("applies_to", "").lower():
                    matching.append(req)
                    break
        return matching

    def check(self, claim_object: str, issue_type: str, vlm: VLMOutput) -> bool:
        matching = self.get_matching(claim_object, issue_type)
        if not matching:
            return vlm.part_visible
        for req in matching:
            text = req.get("minimum_image_evidence", "").lower()
            # Requirement mentions visibility - check part_visible
            if "visible" in text and not vlm.part_visible:
                return False
            # Requirement mentions angle/perspective
            if "angle" in text and vlm.image_quality == "wrong_angle":
                return False
            # Requirement mentions clarity
            if "clearly" in text and vlm.image_quality not in ("good", "fair"):
                return False
            # Requirement mentions part identification
            if "identify" in text and (vlm.object_part == "unknown" if vlm.object_part else True):
                if vlm.visible_part == "unknown" or not vlm.visible_part:
                    return False
        return True


class RuleEngine:
    def __init__(self, history_lookup: HistoryLookup, evidence_csv: str = ""):
        self.history = history_lookup
        self.evidence = EvidenceRequirementChecker(evidence_csv) if evidence_csv else None

    def _derive_risk_flags(self, vlm: VLMOutput) -> list[str]:
        flags = list(vlm.image_quality_flags)
        seen = set(flags)

        if vlm.part_visible and not vlm.damage_visible and vlm.issue_type != "missing_part":
            flag = RiskFlagType.DAMAGE_NOT_VISIBLE.value
            if flag not in seen:
                flags.append(flag)
                seen.add(flag)

        quality_map = {
            "blurry": "blurry_image",
            "low_light": "low_light_or_glare",
            "cropped": "cropped_or_obstructed",
        }
        if vlm.image_quality in quality_map:
            flag = quality_map[vlm.image_quality]
            if flag not in seen:
                flags.append(flag)
                seen.add(flag)

        return flags

    def _fix_issue_type_from_visible_damage(self, vlm: VLMOutput) -> str:
        it = vlm.issue_type
        vd = vlm.visible_damage.lower() if vlm.visible_damage else ""
        vd_tokens = vd.replace(",", " ").replace(".", " ").split()
        vd_text = " ".join(vd_tokens)

        # Score each issue_type by keyword matches in visible_damage
        best_type = it
        best_score = 0
        for candidate, keywords in DAMAGE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in vd_text)
            if score > best_score:
                best_score = score
                best_type = candidate

        # Only override if multiple keywords match
        if best_score >= 2 and best_type != it:
            return best_type
        return it

    def _fix_object_part_from_visible_part(self, vlm: VLMOutput, claim_object: str) -> str:
        if vlm.object_part and vlm.object_part != "unknown":
            return vlm.object_part
        if vlm.visible_part and vlm.visible_part != "unknown":
            vp = vlm.visible_part.lower().replace(" ", "_")
            return vp
        return "unknown"

    def _fix_severity(self, vlm: VLMOutput, fixed_issue_type: str, final_status: str) -> str:
        sev = vlm.severity

        if final_status == ClaimStatus.NOT_ENOUGH_INFORMATION.value:
            return Severity.UNKNOWN.value
        if fixed_issue_type == "none":
            return Severity.NONE.value

        sev_idx = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 4
        if fixed_issue_type in ISSUE_SEVERITY_RANGES:
            floor_idx, cap_idx = ISSUE_SEVERITY_RANGES[fixed_issue_type]
            if sev_idx < floor_idx:
                return SEVERITY_ORDER[floor_idx]
            if sev_idx > cap_idx:
                return SEVERITY_ORDER[cap_idx]

        return sev

    def _confidence_fallback(self, vlm: VLMOutput, risk: list[str]) -> tuple[str, str, str, str, list[str]]:
        cf = vlm.confidence
        if cf >= 0.8:
            return vlm.claim_status, vlm.issue_type, vlm.object_part, vlm.severity, risk

        if cf < 0.3:
            mrr = RiskFlagType.MANUAL_REVIEW_REQUIRED.value
            if mrr not in risk:
                risk.append(mrr)
            return ClaimStatus.NOT_ENOUGH_INFORMATION.value, Severity.UNKNOWN.value, "unknown", Severity.UNKNOWN.value, risk

        if cf < 0.6:
            mrr = RiskFlagType.MANUAL_REVIEW_REQUIRED.value
            if mrr not in risk:
                risk.append(mrr)
            return ClaimStatus.NOT_ENOUGH_INFORMATION.value, vlm.issue_type, vlm.object_part, vlm.severity, risk

        # 0.6-0.8: keep outputs but flag
        mrr = RiskFlagType.MANUAL_REVIEW_REQUIRED.value
        if mrr not in risk:
            risk.append(mrr)
        return vlm.claim_status, vlm.issue_type, vlm.object_part, vlm.severity, risk

    def _apply_consistency_rules(self, status: str, issue: str, obj_part: str, sev: str, evidence_met: bool, risk: list[str]) -> tuple[str, str, str, str, bool, list[str]]:
        # Rule 1: issue_type none → severity none
        if issue == "none" and sev != Severity.NONE.value:
            sev = Severity.NONE.value

        # Rule 2: issue_type unknown → severity unknown
        if issue == "unknown" and sev != Severity.UNKNOWN.value:
            sev = Severity.UNKNOWN.value

        # Rule 3: claim_status NEI → severity unknown only if issue is unknown
        if status == ClaimStatus.NOT_ENOUGH_INFORMATION.value:
            if issue == "unknown" and sev != Severity.UNKNOWN.value:
                sev = Severity.UNKNOWN.value
            evidence_met = False

        # Rule 5: damage not visible + part visible + issue_type is damage → none
        # (handled by _fix_issue_type_from_visible_damage already)

        # Rule 6: severity none → issue_type none (unless unknown)
        if sev == Severity.NONE.value and issue not in ("none", "unknown", "missing_part"):
            issue = "none"

        # Rule 7: valid_image false → evidence_standard_met false (will be applied later)

        # Rule 8: supported → supporting_image_ids not none (applied downstream)

        # Rule 9: missing_part + supported → NEI (already done)

        # Rule 10: confidence < 0.3 → all unknown (handled in _confidence_fallback)

        return status, issue, obj_part, sev, evidence_met, risk

    def apply(self, claim_input, vlm: VLMOutput) -> FinalOutput:
        out = FinalOutput()
        out.user_id = claim_input.user_id
        out.image_paths = claim_input.image_paths
        out.user_claim = claim_input.user_claim
        out.claim_object = claim_input.claim_object

        # Step 1: Fix issue_type and object_part from observation text
        fixed_issue_type = self._fix_issue_type_from_visible_damage(vlm)
        fixed_object_part = self._fix_object_part_from_visible_part(vlm, claim_input.claim_object)

        # Step 2: Build risk flags (derived only)
        risk = self._derive_risk_flags(vlm)

        uid = claim_input.user_id
        if self.history.has_user_history_risk(uid):
            if RiskFlagType.USER_HISTORY_RISK.value not in risk:
                risk.append(RiskFlagType.USER_HISTORY_RISK.value)
        if self.history.needs_manual_review(uid):
            if RiskFlagType.MANUAL_REVIEW_REQUIRED.value not in risk:
                risk.append(RiskFlagType.MANUAL_REVIEW_REQUIRED.value)

        # Step 3: Confidence fallback
        cs, it, op, sev, risk = self._confidence_fallback(vlm, risk)
        if cs != vlm.claim_status:
            fixed_issue_type = it
            fixed_object_part = op

        # Step 4: Determine claim_status
        image_quality_ok = vlm.image_quality in ("good", "fair")
        evidence_met = vlm.part_visible and image_quality_ok

        # Check evidence requirements
        if self.evidence:
            req_met = self.evidence.check(claim_input.claim_object, fixed_issue_type, vlm)
            evidence_met = evidence_met and req_met

        if RiskFlagType.WRONG_OBJECT.value in risk:
            evidence_met = True

        if not evidence_met:
            final_status = ClaimStatus.NOT_ENOUGH_INFORMATION.value
        else:
            final_status = cs

        # Step 5: Contradiction overrides
        if final_status == ClaimStatus.SUPPORTED.value:
            for cf in [RiskFlagType.DAMAGE_NOT_VISIBLE.value, RiskFlagType.WRONG_OBJECT.value, RiskFlagType.CLAIM_MISMATCH.value]:
                if cf in risk:
                    final_status = ClaimStatus.CONTRADICTED.value
                    break

        if final_status == ClaimStatus.SUPPORTED.value and not vlm.damage_visible and fixed_issue_type != "missing_part":
            final_status = ClaimStatus.CONTRADICTED.value

        if fixed_issue_type == "missing_part" and final_status == ClaimStatus.SUPPORTED.value:
            final_status = ClaimStatus.NOT_ENOUGH_INFORMATION.value

        # Step 6: Fix severity
        fixed_severity = self._fix_severity(vlm, fixed_issue_type, final_status)

        # Step 7: Apply consistency rules
        final_status, fixed_issue_type, fixed_object_part, fixed_severity, evidence_met, risk = \
            self._apply_consistency_rules(final_status, fixed_issue_type, fixed_object_part, fixed_severity, evidence_met, risk)

        # Step 8: Populate output
        evidence_met = evidence_met and final_status != ClaimStatus.NOT_ENOUGH_INFORMATION.value
        out.evidence_standard_met = "true" if evidence_met else "false"
        out.evidence_standard_met_reason = vlm.evidence_standard_met_reason
        out.risk_flags = ";".join(risk) if risk else "none"

        out.issue_type = fixed_issue_type
        out.object_part = fixed_object_part
        out.claim_status = final_status
        out.claim_status_justification = vlm.claim_status_justification

        if vlm.supporting_image_ids:
            out.supporting_image_ids = ";".join(vlm.supporting_image_ids)
        else:
            out.supporting_image_ids = "none"
        if final_status == ClaimStatus.NOT_ENOUGH_INFORMATION.value:
            out.supporting_image_ids = "none"

        v = vlm.valid_image
        if RiskFlagType.NON_ORIGINAL_IMAGE.value in risk:
            v = False
        out.valid_image = "true" if v else "false"

        out.severity = fixed_severity

        return out

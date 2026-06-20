from typing import Optional, Any
from pydantic import BaseModel, Field
from .enums import (
    IssueType, ClaimStatus, Severity, RiskFlagType,
    object_part_values,
)


class ClaimInput:
    def __init__(self, user_id="", image_paths="", user_claim="", claim_object="", image_path_list=None):
        self.user_id = user_id
        self.image_paths = image_paths
        self.user_claim = user_claim
        self.claim_object = claim_object
        if image_path_list is None:
            self.image_path_list = [p.strip() for p in self.image_paths.split(";") if p.strip()]
        else:
            self.image_path_list = image_path_list


class VLMOutput(BaseModel):
    part_visible: bool = True
    damage_visible: bool = True
    image_quality: str = "good"
    visible_damage: str = ""
    visible_part: str = ""
    issue_type: str = "unknown"
    object_part: str = "unknown"
    claim_status: str = "supported"
    severity: str = "medium"
    valid_image: bool = True
    supporting_image_ids: list[str] = Field(default_factory=list)
    evidence_standard_met_reason: str = ""
    claim_status_justification: str = ""
    image_quality_flags: list[str] = Field(default_factory=list)
    confidence: float = 1.0


    @staticmethod
    def json_schema_dict() -> dict:
        return {
            "type": "object",
            "properties": {
                "part_visible": {"type": "boolean"},
                "damage_visible": {"type": "boolean"},
                "image_quality": {"type": "string"},
                "visible_damage": {"type": "string"},
                "visible_part": {"type": "string"},
                "issue_type": {"type": "string"},
                "object_part": {"type": "string"},
                "claim_status": {"type": "string"},
                "severity": {"type": "string"},
                "valid_image": {"type": "boolean"},
                "supporting_image_ids": {"type": "array", "items": {"type": "string"}},
                "evidence_standard_met_reason": {"type": "string"},
                "claim_status_justification": {"type": "string"},
                "image_quality_flags": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
            },
            "required": [
                "part_visible", "damage_visible", "image_quality",
                "visible_damage", "visible_part",
                "issue_type", "object_part", "claim_status",
                "severity", "valid_image", "supporting_image_ids",
                "evidence_standard_met_reason", "claim_status_justification",
                "image_quality_flags", "confidence",
            ],
        }


class VLMOutputStrategyA:
    def __init__(self, evidence_standard_met=True, evidence_standard_met_reason="",
                 risk_flags="none", issue_type="unknown", object_part="unknown",
                 claim_status="supported", claim_status_justification="",
                 supporting_image_ids="none", valid_image=True, severity="medium"):
        self.evidence_standard_met = evidence_standard_met
        self.evidence_standard_met_reason = evidence_standard_met_reason
        self.risk_flags = risk_flags
        self.issue_type = issue_type
        self.object_part = object_part
        self.claim_status = claim_status
        self.claim_status_justification = claim_status_justification
        self.supporting_image_ids = supporting_image_ids
        self.valid_image = valid_image
        self.severity = severity


class FinalOutput:
    def __init__(self):
        self.user_id = ""
        self.image_paths = ""
        self.user_claim = ""
        self.claim_object = ""
        self.evidence_standard_met = "true"
        self.evidence_standard_met_reason = ""
        self.risk_flags = "none"
        self.issue_type = ""
        self.object_part = ""
        self.claim_status = ""
        self.claim_status_justification = ""
        self.supporting_image_ids = "none"
        self.valid_image = "true"
        self.severity = ""

    def csv_row(self) -> str:
        def esc(v):
            s = str(v)
            if "," in s or '"' in s or "\n" in s:
                s = '"' + s.replace('"', '""') + '"'
            return s
        cols = [
            self.user_id, self.image_paths, self.user_claim, self.claim_object,
            self.evidence_standard_met, self.evidence_standard_met_reason,
            self.risk_flags, self.issue_type, self.object_part,
            self.claim_status, self.claim_status_justification,
            self.supporting_image_ids, self.valid_image, self.severity,
        ]
        return ",".join(esc(c) for c in cols)

    @staticmethod
    def csv_header() -> str:
        return (
            "user_id,image_paths,user_claim,claim_object,"
            "evidence_standard_met,evidence_standard_met_reason,"
            "risk_flags,issue_type,object_part,"
            "claim_status,claim_status_justification,"
            "supporting_image_ids,valid_image,severity"
        )


class TelemetryRecord:
    def __init__(self):
        self.strategy = ""
        self.model_calls = 0
        self.images_processed = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.runtime_seconds = 0.0
        self.cost_estimate = 0.0
        self.total_images = 0
        self.avg_confidence = 0.0


def constrain_issue_type(value: str) -> str:
    allowed = IssueType.all_values()
    if value in allowed:
        return value
    return "unknown"


def constrain_claim_status(value: str) -> str:
    allowed = ClaimStatus.all_values()
    if value in allowed:
        return value
    return "not_enough_information"


def constrain_severity(value: str) -> str:
    allowed = Severity.all_values()
    if value in allowed:
        return value
    return "unknown"


def constrain_object_part(value: str, claim_object: str) -> str:
    allowed = object_part_values(claim_object)
    if value in allowed:
        return value
    normalized = value.lower().replace(" ", "_")
    if normalized in allowed:
        return normalized
    # Known aliases
    aliases = {
        "side_mirror": "side_mirror",
        "mirror": "side_mirror",
        "package_exterior": "package_side",
        "packaging_side": "package_side",
        "packaging_seal": "seal",
        "packaging_corner": "package_corner",
        "food_can": "unknown",
        "contents": "contents",
        "interior": "contents",
    }
    if normalized in aliases:
        result = aliases[normalized]
        if result in allowed:
            return result
    # Fuzzy: normalize both sides
    for a in allowed:
        a_norm = a.replace("_", "")
        norm = normalized.replace("_", "")
        if norm in a_norm or a_norm in norm:
            return a
    return "unknown"

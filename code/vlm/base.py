import json
from abc import ABC, abstractmethod
from typing import Optional
from models.schemas import VLMOutput, VLMOutputStrategyA, ClaimInput
from telemetry.tracker import TelemetryTracker


def _image_id_from_path(path: str) -> str:
    import os
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name


class VLMClient(ABC):
    def __init__(self, model: str = "", telemetry: Optional[TelemetryTracker] = None):
        self.model = model
        self.telemetry = telemetry or TelemetryTracker()

    @abstractmethod
    def _call_api(self, prompt: str, image_paths: list[str], json_schema: dict) -> tuple[str, int, int]:
        ...

    def _count_images(self, image_paths: list[str]) -> int:
        return len(image_paths)

    def _image_list_text(self, image_paths: list[str]) -> str:
        ids = [_image_id_from_path(p) for p in image_paths]
        return "Submitted image IDs: " + ", ".join(ids) + "\nUse these exact IDs in supporting_image_ids."

    def predict_strategy_b(self, claim: ClaimInput, prompt_template: str) -> VLMOutput:
        image_list_text = self._image_list_text(claim.image_path_list)

        prompt = prompt_template.replace("{user_claim}", claim.user_claim)
        prompt = prompt.replace("{claim_object}", claim.claim_object)
        prompt += "\n\n" + image_list_text

        schema = {
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

        raw, inp_tok, out_tok = self._call_api(prompt, claim.image_path_list, schema)
        n_images = self._count_images(claim.image_path_list)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._default_strategy_b()

        if not isinstance(data, dict):
            data = self._default_strategy_b()

        result = VLMOutput(
            part_visible=data.get("part_visible", True),
            damage_visible=data.get("damage_visible", True),
            image_quality=data.get("image_quality", "good"),
            visible_damage=data.get("visible_damage", ""),
            visible_part=data.get("visible_part", ""),
            issue_type=data.get("issue_type", "unknown"),
            object_part=data.get("object_part", "unknown"),
            claim_status=data.get("claim_status", "supported"),
            severity=data.get("severity", "medium"),
            valid_image=data.get("valid_image", True),
            supporting_image_ids=data.get("supporting_image_ids", []),
            evidence_standard_met_reason=data.get("evidence_standard_met_reason", ""),
            claim_status_justification=data.get("claim_status_justification", ""),
            image_quality_flags=data.get("image_quality_flags", []),
            confidence=data.get("confidence", 0.5),
        )

        if self.telemetry:
            self.telemetry.record_call(
                input_tokens=inp_tok,
                output_tokens=out_tok,
                images=n_images,
                confidence=result.confidence,
            )

        return result

    def predict_strategy_a(self, claim: ClaimInput, prompt_template: str) -> VLMOutputStrategyA:
        image_list_text = self._image_list_text(claim.image_path_list)

        prompt = prompt_template.replace("{user_claim}", claim.user_claim)
        prompt = prompt.replace("{claim_object}", claim.claim_object)
        prompt += "\n\n" + image_list_text

        schema = {
            "type": "object",
            "properties": {
                "evidence_standard_met": {"type": "boolean"},
                "evidence_standard_met_reason": {"type": "string"},
                "risk_flags": {"type": "string"},
                "issue_type": {"type": "string"},
                "object_part": {"type": "string"},
                "claim_status": {"type": "string"},
                "claim_status_justification": {"type": "string"},
                "supporting_image_ids": {"type": "string"},
                "valid_image": {"type": "boolean"},
                "severity": {"type": "string"},
            },
            "required": [
                "evidence_standard_met", "evidence_standard_met_reason",
                "risk_flags", "issue_type", "object_part",
                "claim_status", "claim_status_justification",
                "supporting_image_ids", "valid_image", "severity",
            ],
        }

        raw, inp_tok, out_tok = self._call_api(prompt, claim.image_path_list, schema)
        n_images = self._count_images(claim.image_path_list)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._default_strategy_a()

        if not isinstance(data, dict):
            data = self._default_strategy_a()

        result = VLMOutputStrategyA(
            evidence_standard_met=data.get("evidence_standard_met", True),
            evidence_standard_met_reason=data.get("evidence_standard_met_reason", ""),
            risk_flags=data.get("risk_flags", "none"),
            issue_type=data.get("issue_type", "unknown"),
            object_part=data.get("object_part", "unknown"),
            claim_status=data.get("claim_status", "supported"),
            claim_status_justification=data.get("claim_status_justification", ""),
            supporting_image_ids=data.get("supporting_image_ids", "none"),
            valid_image=data.get("valid_image", True),
            severity=data.get("severity", "medium"),
        )

        if self.telemetry:
            self.telemetry.record_call(input_tokens=inp_tok, output_tokens=out_tok, images=n_images)

        return result

    def _default_strategy_b(self) -> dict:
        return {
            "part_visible": False,
            "damage_visible": False,
            "image_quality": "unknown",
            "visible_damage": "",
            "visible_part": "",
            "issue_type": "unknown",
            "object_part": "unknown",
            "claim_status": "not_enough_information",
            "severity": "unknown",
            "valid_image": True,
            "supporting_image_ids": [],
            "evidence_standard_met_reason": "Could not parse VLM output.",
            "claim_status_justification": "VLM output could not be parsed.",
            "image_quality_flags": [],
            "confidence": 0.0,
        }

    def _default_strategy_a(self) -> dict:
        return {
            "evidence_standard_met": False,
            "evidence_standard_met_reason": "VLM output could not be parsed.",
            "risk_flags": "manual_review_required",
            "issue_type": "unknown",
            "object_part": "unknown",
            "claim_status": "not_enough_information",
            "claim_status_justification": "VLM output could not be parsed.",
            "supporting_image_ids": "none",
            "valid_image": False,
            "severity": "unknown",
        }

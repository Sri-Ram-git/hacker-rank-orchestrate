import base64
import json
import os
from vlm.base import VLMClient
from typing import Optional
from telemetry.tracker import TelemetryTracker


class OpenAIClient(VLMClient):
    def __init__(
        self,
        model: str = "gpt-4o-2024-08-06",
        api_key: Optional[str] = None,
        telemetry: Optional[TelemetryTracker] = None,
    ):
        super().__init__(model=model, telemetry=telemetry)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _detect_media_type(self, path: str) -> str:
        ext = path.lower().split(".")[-1] if "." in path else "jpg"
        mapping = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        return mapping.get(ext, "image/jpeg")

    def _call_api(self, prompt: str, image_paths: list[str], json_schema: dict) -> tuple[str, int, int]:
        if not self.api_key:
            return self._mock_call()

        try:
            from openai import OpenAI
        except ImportError:
            return self._mock_call()

        client = OpenAI(api_key=self.api_key)

        content = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            if os.path.exists(img_path):
                b64 = self._encode_image(img_path)
                media = self._detect_media_type(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media};base64,{b64}", "detail": "auto"},
                })

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            max_tokens=1024,
        )

        raw = response.choices[0].message.content if response.choices else "{}"
        usage = response.usage
        inp = usage.prompt_tokens if usage else 0
        out = usage.completion_tokens if usage else 0
        return raw, inp, out

    def _mock_call(self) -> tuple[str, int, int]:
        return (
            json.dumps({
                "part_visible": True,
                "damage_visible": True,
                "image_quality": "good",
                "visible_damage": "visible damage",
                "visible_part": "visible part",
                "issue_type": "unknown",
                "object_part": "unknown",
                "claim_status": "supported",
                "severity": "medium",
                "valid_image": True,
                "supporting_image_ids": ["img_1"],
                "evidence_standard_met_reason": "Mock VLM: no API key configured.",
                "claim_status_justification": "Mock VLM: no API key configured.",
                "image_quality_flags": [],
                "confidence": 0.5,
            }),
            100,
            50,
        )

import base64
import json
import os
from vlm.base import VLMClient
from typing import Optional
from telemetry.tracker import TelemetryTracker


class AnthropicClient(VLMClient):
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        telemetry: Optional[TelemetryTracker] = None,
    ):
        super().__init__(model=model, telemetry=telemetry)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

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
            import anthropic
        except ImportError:
            return self._mock_call()

        client = anthropic.Anthropic(api_key=self.api_key)

        content_blocks = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            if os.path.exists(img_path):
                b64 = self._encode_image(img_path)
                media = self._detect_media_type(img_path)
                content_blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media, "data": b64},
                })

        msg = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content_blocks}],
        )

        raw = msg.content[0].text if msg.content else "{}"
        inp = msg.usage.input_tokens if msg.usage else 0
        out = msg.usage.output_tokens if msg.usage else 0
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

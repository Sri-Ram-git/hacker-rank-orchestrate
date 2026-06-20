import json
import os
import sys
import time
from typing import Optional
from vlm.base import VLMClient

from telemetry.tracker import TelemetryTracker
from google.genai import types


class GeminiClient(VLMClient):
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        telemetry: Optional[TelemetryTracker] = None,
        min_delay: float = 12.0,
    ):
        super().__init__(model=model, telemetry=telemetry)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.min_delay = min_delay
        self._last_request_time = 0.0
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            self._client = None
        return self._client

    def _load_image(self, path: str):
        try:
            from PIL import Image
            return Image.open(path)
        except ImportError:
            return None

    def _call_api(self, prompt: str, image_paths: list[str], json_schema: dict) -> tuple[str, int, int]:
        client = self._get_client()
        if client is None:
            return self._mock_call()

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        contents = [prompt]
        for path in image_paths:
            if os.path.exists(path):
                img = self._load_image(path)
                if img is not None:
                    contents.append(img)

        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=json_schema,
        )

        max_retries = 8
        last_error = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                self._last_request_time = time.time()
                raw = response.text if response.text else "{}"
                usage = response.usage_metadata
                inp = usage.prompt_token_count if usage else 0
                out = usage.candidates_token_count if usage else 0
                return raw, inp, out
            except Exception as e:
                last_error = e
                err_str = str(e)

                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 10.0 * (attempt + 1)
                    print(f"  [429] rate limited, waiting {wait:.0f}s (attempt {attempt+1})...")
                    sys.stdout.flush()
                    time.sleep(wait)

                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    wait = 15.0 * (attempt + 1)
                    print(f"  [503] model overloaded, waiting {wait:.0f}s (attempt {attempt+1})...")
                    sys.stdout.flush()
                    time.sleep(wait)

                elif "400" in err_str or "INVALID_ARGUMENT" in err_str:
                    print(f"  [400] invalid request: {err_str[:200]}")
                    print(f"  Skipping this claim with fallback...")
                    return self._mock_call()

                else:
                    if attempt < max_retries - 1:
                        wait = 10.0 * (attempt + 1)
                        print(f"  [{err_str[:30]}] retrying in {wait:.0f}s (attempt {attempt+1})...")
                        sys.stdout.flush()
                        time.sleep(wait)
                    else:
                        raise

        if last_error:
            raise last_error
        return self._mock_call()

    def _mock_call(self) -> tuple[str, int, int]:
        return (
            json.dumps({
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
                "evidence_standard_met_reason": "Gemini API call failed after retries.",
                "claim_status_justification": "Gemini API call failed after retries.",
                "image_quality_flags": ["manual_review_required"],
                "confidence": 0.0,
            }),
            100,
            50,
        )

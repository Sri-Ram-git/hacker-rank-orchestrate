import time


class TelemetryTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.images_processed = 0
        self.total_images = 0
        self.start_time = None
        self.end_time = None
        self.confidence_scores = []
        self.claim_runtimes = []

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def record_call(self, input_tokens=0, output_tokens=0, images=0, confidence=None):
        self.model_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.images_processed += images
        if confidence is not None:
            self.confidence_scores.append(confidence)

    def record_claim_runtime(self, seconds):
        self.claim_runtimes.append(seconds)

    @property
    def runtime_seconds(self):
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def avg_confidence(self):
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)

    def estimate_cost(self, model="claude-sonnet-4-20250514"):
        pricing = {
            "claude-sonnet-4-20250514": (3.0, 15.0),
            "claude-3-5-sonnet-20241022": (3.0, 15.0),
            "gpt-4o-2024-08-06": (2.5, 10.0),
            "gpt-4o-mini": (0.15, 0.60),
        }
        if model not in pricing:
            model = "gpt-4o-mini"
        input_price, output_price = pricing[model]
        input_cost = (self.input_tokens / 1_000_000) * input_price
        output_cost = (self.output_tokens / 1_000_000) * output_price
        return round(input_cost + output_cost, 6)

    def summary(self, strategy="", model="claude-sonnet-4-20250514"):
        return {
            "strategy": strategy,
            "model_calls": self.model_calls,
            "images_processed": self.images_processed,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "runtime_seconds": round(self.runtime_seconds, 2),
            "cost_estimate": self.estimate_cost(model),
            "avg_confidence": round(self.avg_confidence, 3),
            "model": model,
        }

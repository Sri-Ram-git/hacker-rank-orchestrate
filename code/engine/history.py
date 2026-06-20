import csv
import os
from typing import Optional


class HistoryLookup:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row.get("user_id", "")
                self._data[uid] = {
                    "user_id": uid,
                    "past_claim_count": int(row.get("past_claim_count", "0")),
                    "accept_claim": int(row.get("accept_claim", "0")),
                    "manual_review_claim": int(row.get("manual_review_claim", "0")),
                    "rejected_claim": int(row.get("rejected_claim", "0")),
                    "last_90_days_claim_count": int(row.get("last_90_days_claim_count", "0")),
                    "history_flags": row.get("history_flags", "none"),
                    "history_summary": row.get("history_summary", ""),
                }

    def get(self, user_id: str) -> Optional[dict]:
        return self._data.get(user_id)

    def has_user_history_risk(self, user_id: str) -> bool:
        record = self.get(user_id)
        if record is None:
            return False
        flags = record.get("history_flags", "none")
        return "user_history_risk" in flags

    def needs_manual_review(self, user_id: str) -> bool:
        record = self.get(user_id)
        if record is None:
            return False
        flags = record.get("history_flags", "none")
        if "manual_review_required" in flags:
            return True
        if record.get("manual_review_claim", 0) > 0:
            return True
        return False

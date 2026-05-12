import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from util.config import get_config_path


class CS2CaseAPIError(Exception):
    """Raised when CS2 case API calls fail."""


class CS2CaseClient:
    """Simple client for pulling CS2 case items from a public crate API."""

    CRATES_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/crates.json"

    def __init__(self, timeout: float = 8.0, max_retries: int = 1):
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self._logger = logging.getLogger(__name__)
        self._session = requests.Session()

        self._cache_ttl_seconds = int(os.getenv("CS2_CASE_CACHE_TTL_SECONDS", "86400"))
        configured_cache_path = os.getenv("CS2_CASE_CACHE_PATH", "").strip()
        if configured_cache_path:
            self._cache_path = Path(configured_cache_path)
        else:
            config_dir = Path(get_config_path()).parent
            self._cache_path = config_dir / "cache" / "cs2_crates_cache.json"

        self._crates: List[Dict[str, Any]] = []
        self._load_cached_crates()

    def _load_cached_crates(self) -> None:
        try:
            if not self._cache_path.exists():
                return
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            updated_at = float(payload.get("updated_at", 0))
            crates = payload.get("crates", [])
            if not isinstance(crates, list):
                return
            if (time.time() - updated_at) > self._cache_ttl_seconds:
                return
            self._crates = crates
            self._logger.info("Loaded CS2 crates cache entries=%s path=%s", len(crates), self._cache_path)
        except Exception:
            self._logger.exception("Failed loading CS2 crates cache from %s", self._cache_path)

    def _save_cached_crates(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.time(),
                "crates": self._crates,
            }
            self._cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed saving CS2 crates cache to %s", self._cache_path)

    def _fetch_crates(self) -> List[Dict[str, Any]]:
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._session.get(self.CRATES_URL, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    raise CS2CaseAPIError("Unexpected crates payload shape")
                self._crates = data
                self._save_cached_crates()
                return data
            except Exception as exc:
                self._logger.warning(
                    "CS2 crates fetch failed (attempt %s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt >= attempts:
                    raise CS2CaseAPIError(str(exc)) from exc
                time.sleep(0.35 * attempt)
        raise CS2CaseAPIError("Failed to fetch CS2 crates")

    def _ensure_crates(self) -> List[Dict[str, Any]]:
        if self._crates:
            return self._crates
        return self._fetch_crates()

    def prewarm_cases(self, case_names: List[str]) -> None:
        try:
            crates = self._ensure_crates()
        except CS2CaseAPIError:
            self._logger.exception("CS2 case prewarm failed")
            return

        names = [n.strip().lower() for n in case_names if isinstance(n, str) and n.strip()]
        if not names:
            return
        found = sum(1 for c in crates if c.get("name", "").strip().lower() in names)
        self._logger.info("CS2 case prewarm ready requested=%s found=%s", len(names), found)

    @staticmethod
    def _item_price(item: Dict[str, Any], knife_hit: bool = False) -> float:
        if knife_hit:
            return round(random.uniform(250.0, 2500.0), 2)

        rarity_name = ((item.get("rarity") or {}).get("name") or "").lower()
        if "covert" in rarity_name:
            return round(random.uniform(80.0, 450.0), 2)
        if "classified" in rarity_name:
            return round(random.uniform(25.0, 120.0), 2)
        if "restricted" in rarity_name:
            return round(random.uniform(8.0, 40.0), 2)
        if "mil-spec" in rarity_name:
            return round(random.uniform(1.0, 12.0), 2)
        return round(random.uniform(3.0, 20.0), 2)

    def pull_case_item(self, case_name: str, knife_pull_chance: float = 0.0025) -> Dict[str, Any]:
        if not case_name:
            raise CS2CaseAPIError("Missing case_name")

        crates = self._ensure_crates()
        case_name_l = case_name.strip().lower()
        crate = next((c for c in crates if c.get("name", "").strip().lower() == case_name_l), None)
        if not crate:
            raise CS2CaseAPIError(f"Case '{case_name}' not found in API")

        contains = crate.get("contains") or []
        contains_rare = crate.get("contains_rare") or []
        roll_knife = random.random() < max(0.0, min(1.0, knife_pull_chance))

        knife_hit = bool(roll_knife and contains_rare)
        if knife_hit:
            pulled = random.choice(contains_rare)
        elif contains:
            pulled = random.choice(contains)
        elif contains_rare:
            pulled = random.choice(contains_rare)
            knife_hit = True
        else:
            raise CS2CaseAPIError(f"Case '{case_name}' has no pullable items")

        rarity_name = ((pulled.get("rarity") or {}).get("name") or "Unknown")
        return {
            "name": pulled.get("name", "Unknown Item"),
            "rarity": rarity_name,
            "price": self._item_price(pulled, knife_hit=knife_hit),
            "knife_hit": knife_hit,
            "case_name": crate.get("name", case_name),
        }

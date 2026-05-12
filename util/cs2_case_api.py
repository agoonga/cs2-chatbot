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
    STEAM_PRICE_URL = "https://steamcommunity.com/market/priceoverview/"

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
        self._case_price_cache: Dict[str, float] = {}
        self._item_price_cache: Dict[str, float] = {}
        self._load_cached_crates()

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            parsed = float(value)
            return parsed if parsed >= 0 else None
        except Exception:
            return None

    @staticmethod
    def _parse_steam_price(raw_value: Any) -> Optional[float]:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return round(float(raw_value), 2)

        text = str(raw_value).strip()
        if not text:
            return None

        # Keep digits and separators, then normalize to dot decimal.
        filtered = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
        if not filtered:
            return None

        if filtered.count(",") > 0 and filtered.count(".") > 0:
            filtered = filtered.replace(",", "")
        elif filtered.count(",") > 0 and filtered.count(".") == 0:
            filtered = filtered.replace(",", ".")

        try:
            return round(float(filtered), 2)
        except Exception:
            return None

    def _load_cached_crates(self) -> None:
        try:
            if not self._cache_path.exists():
                return
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            updated_at = float(payload.get("updated_at", 0))
            crates = payload.get("crates", [])
            case_prices = payload.get("case_prices", {})
            item_prices = payload.get("item_prices", {})
            if not isinstance(crates, list):
                return
            if (time.time() - updated_at) > self._cache_ttl_seconds:
                return
            self._crates = crates
            if isinstance(case_prices, dict):
                self._case_price_cache = {
                    str(k).strip().lower(): v
                    for k, v in case_prices.items()
                    if self._safe_float(v) is not None
                }
            if isinstance(item_prices, dict):
                self._item_price_cache = {
                    str(k).strip().lower(): v
                    for k, v in item_prices.items()
                    if self._safe_float(v) is not None
                }
            self._logger.info("Loaded CS2 crates cache entries=%s path=%s", len(crates), self._cache_path)
        except Exception:
            self._logger.exception("Failed loading CS2 crates cache from %s", self._cache_path)

    def _save_cached_crates(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.time(),
                "crates": self._crates,
                "case_prices": self._case_price_cache,
                "item_prices": self._item_price_cache,
            }
            self._cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed saving CS2 crates cache to %s", self._cache_path)

    def _fetch_steam_price(self, market_hash_name: str) -> Optional[float]:
        name = (market_hash_name or "").strip()
        if not name:
            return None

        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = self._session.get(
                    self.STEAM_PRICE_URL,
                    params={
                        "appid": 730,
                        "currency": 1,
                        "market_hash_name": name,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not payload.get("success"):
                    return None

                price = self._parse_steam_price(payload.get("lowest_price"))
                if price is None:
                    price = self._parse_steam_price(payload.get("median_price"))
                return price
            except Exception as exc:
                self._logger.warning(
                    "Steam price fetch failed name=%s (attempt %s/%s): %s",
                    name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt >= attempts:
                    return None
                time.sleep(0.25 * attempt)

        return None

    def get_case_price(self, case_name: str, refresh: bool = False) -> Optional[float]:
        key = (case_name or "").strip().lower()
        if not key:
            return None

        if not refresh and key in self._case_price_cache:
            return self._safe_float(self._case_price_cache[key])

        price = self._fetch_steam_price(case_name)
        if price is None:
            return self._safe_float(self._case_price_cache.get(key))

        self._case_price_cache[key] = price
        self._save_cached_crates()
        return price

    def get_item_price(self, item_name: str, refresh: bool = False) -> Optional[float]:
        key = (item_name or "").strip().lower()
        if not key:
            return None

        if not refresh and key in self._item_price_cache:
            return self._safe_float(self._item_price_cache[key])

        price = self._fetch_steam_price(item_name)
        if price is None:
            return self._safe_float(self._item_price_cache.get(key))

        self._item_price_cache[key] = price
        self._save_cached_crates()
        return price

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
        priced = 0
        for name in case_names:
            if not isinstance(name, str) or not name.strip():
                continue
            if self.get_case_price(name.strip()) is not None:
                priced += 1

        self._logger.info(
            "CS2 case prewarm ready requested=%s found=%s priced=%s",
            len(names),
            found,
            priced,
        )

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
        market_price = self.get_item_price(pulled.get("name", ""))
        return {
            "name": pulled.get("name", "Unknown Item"),
            "rarity": rarity_name,
            "price": market_price if market_price is not None else self._item_price(pulled, knife_hit=knife_hit),
            "knife_hit": knife_hit,
            "case_name": crate.get("name", case_name),
        }

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from util.config import get_config_path


class MTGTCGAPIError(Exception):
    """Raised when MTG API calls fail."""


class MTGTCGClient:
    """Small wrapper around Scryfall card API for MTG pack pulls."""

    BASE_URL = "https://api.scryfall.com"

    def __init__(self, timeout: float = 8.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self._logger = logging.getLogger(__name__)
        self._session = requests.Session()

        self._cache_ttl_seconds = int(os.getenv("MTG_TCG_CACHE_TTL_SECONDS", "43200"))
        configured_cache_path = os.getenv("MTG_TCG_CACHE_PATH", "").strip()
        if configured_cache_path:
            self._cache_path = Path(configured_cache_path)
        else:
            config_dir = Path(get_config_path()).parent
            self._cache_path = config_dir / "cache" / "mtg_tcg_cache.json"

        self._set_name_cache: Dict[str, str] = {}
        self._load_persistent_cache()

    def _load_persistent_cache(self) -> None:
        try:
            if not self._cache_path.exists():
                return
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            updated_at = float(payload.get("updated_at", 0))
            if (time.time() - updated_at) > self._cache_ttl_seconds:
                return
            set_names = payload.get("set_names", {})
            if isinstance(set_names, dict):
                self._set_name_cache = {
                    str(k).strip().lower(): str(v)
                    for k, v in set_names.items()
                    if isinstance(k, str) and isinstance(v, str)
                }
        except Exception:
            self._logger.exception("Failed loading MTG cache from %s", self._cache_path)

    def _save_persistent_cache(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.time(),
                "set_names": self._set_name_cache,
            }
            self._cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed saving MTG cache to %s", self._cache_path)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        attempts = self.max_retries + 1
        request_params = params or {}

        for attempt in range(1, attempts + 1):
            try:
                response = self._session.get(url, params=request_params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as exc:
                self._logger.warning(
                    "MTG API request failed (attempt %s/%s) path=%s params=%s error=%s",
                    attempt,
                    attempts,
                    path,
                    request_params,
                    exc,
                )
                if attempt >= attempts:
                    raise MTGTCGAPIError(str(exc)) from exc
                time.sleep(0.35 * attempt)

        raise MTGTCGAPIError("Request failed")

    def _set_name(self, set_code: str) -> str:
        key = (set_code or "").strip().lower()
        if not key:
            return "Unknown Set"

        cached = self._set_name_cache.get(key)
        if cached:
            return cached

        payload = self._get(f"/sets/{key}")
        set_name = payload.get("name") or set_code
        self._set_name_cache[key] = str(set_name)
        self._save_persistent_cache()
        return str(set_name)

    @staticmethod
    def _is_good_card(card: Dict[str, Any]) -> bool:
        rarity = (card.get("rarity") or "").lower()
        prices = card.get("prices", {}) if isinstance(card.get("prices"), dict) else {}
        for key in ("usd", "usd_foil", "usd_etched"):
            value = prices.get(key)
            try:
                if value is not None and float(value) >= 10.0:
                    return True
            except (TypeError, ValueError):
                continue
        return rarity in {"mythic", "special", "bonus"}

    @staticmethod
    def _card_price(card: Dict[str, Any]) -> float:
        prices = card.get("prices", {}) if isinstance(card.get("prices"), dict) else {}
        for key in ("usd", "usd_foil", "usd_etched"):
            value = prices.get(key)
            try:
                if value is not None:
                    parsed = float(value)
                    if parsed > 0:
                        return round(parsed, 2)
            except (TypeError, ValueError):
                continue
        return 0.25

    def prewarm_sets(self, set_codes) -> None:
        for code in set_codes:
            if not isinstance(code, str) or not code.strip():
                continue
            try:
                self._set_name(code.strip())
            except MTGTCGAPIError:
                self._logger.exception("MTG prewarm failed for set=%s", code)

    def _pull_random_card(self, query: str) -> Dict[str, Any]:
        return self._get("/cards/random", params={"q": query})

    def pull_pack_card(self, set_code: str, good_pull_chance: float = 0.05) -> Dict[str, Any]:
        set_code = (set_code or "").strip().lower()
        if not set_code:
            raise MTGTCGAPIError("Missing set_code")

        set_name = self._set_name(set_code)
        should_pull_good = random.random() < max(0.0, min(1.0, good_pull_chance))

        card = None
        if should_pull_good:
            for extra in (" (rarity:mythic OR usd>=10)", " rarity:mythic", " usd>=10"):
                try:
                    card = self._pull_random_card(f"set:{set_code}{extra}")
                    if card:
                        break
                except MTGTCGAPIError:
                    continue

        if not card:
            card = self._pull_random_card(f"set:{set_code} game:paper")

        good_hit = self._is_good_card(card)
        return {
            "name": card.get("name", "Unknown Card"),
            "rarity": str(card.get("rarity", "unknown")).title(),
            "set_name": set_name,
            "price": self._card_price(card),
            "good_hit": good_hit,
        }

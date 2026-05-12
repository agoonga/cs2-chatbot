import random
import time
import logging
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from util.config import get_config_path


class PokemonTCGAPIError(Exception):
    """Raised when Pokemon TCG API calls fail."""


class PokemonTCGClient:
    """Small client wrapper around https://api.pokemontcg.io/v2."""

    BASE_URL = "https://api.pokemontcg.io/v2"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 10.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._count_cache: Dict[str, int] = {}
        self._logger = logging.getLogger(__name__)
        self._cache_ttl_seconds = int(os.getenv("POKEMON_TCG_CACHE_TTL_SECONDS", "43200"))

        configured_cache_path = os.getenv("POKEMON_TCG_CACHE_PATH", "").strip()
        if configured_cache_path:
            self._cache_path = Path(configured_cache_path)
        else:
            config_dir = Path(get_config_path()).parent
            self._cache_path = config_dir / "cache" / "pokemon_tcg_cache.json"

        self._session = requests.Session()
        if api_key:
            self._session.headers.update({"X-Api-Key": api_key})

        self._load_persistent_cache()

    def _load_persistent_cache(self) -> None:
        try:
            if not self._cache_path.exists():
                return

            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return

            now = time.time()
            loaded_sets = 0
            for set_id, entry in payload.items():
                if not isinstance(entry, dict):
                    continue

                updated_at = entry.get("updated_at", 0)
                cards = entry.get("cards", [])
                if not isinstance(cards, list) or not cards:
                    continue

                if (now - float(updated_at)) > self._cache_ttl_seconds:
                    continue

                self._cache[set_id] = cards
                loaded_sets += 1

            if loaded_sets:
                self._logger.info(
                    "Loaded Pokemon TCG cache from disk sets=%s path=%s",
                    loaded_sets,
                    self._cache_path,
                )
        except Exception:
            self._logger.exception("Failed loading Pokemon TCG cache from %s", self._cache_path)

    def _save_persistent_cache(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            now = time.time()
            payload = {
                set_id: {
                    "updated_at": now,
                    "cards": cards,
                }
                for set_id, cards in self._cache.items()
                if cards
            }
            self._cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed saving Pokemon TCG cache to %s", self._cache_path)

    def prewarm_sets(self, set_ids: List[str], sample_size: int = 120) -> None:
        """Preload a sample of cards for each set to reduce open-time API latency."""
        unique_sets = [s for s in dict.fromkeys(set_ids) if isinstance(s, str) and s.strip()]
        for set_id in unique_sets:
            try:
                self._warm_set_sample(set_id.strip(), sample_size=sample_size)
            except PokemonTCGAPIError:
                self._logger.exception("Pokemon TCG prewarm failed for set_id=%s", set_id)

    def _warm_set_sample(self, set_id: str, sample_size: int = 120) -> None:
        if set_id in self._cache and self._cache[set_id]:
            return

        query = f"set.id:{set_id}"
        total = self._count_query(query)
        if total <= 0:
            raise PokemonTCGAPIError(f"No cards found for set '{set_id}'.")

        target = min(sample_size, total)
        page_size = min(250, target)
        payload = self._get(
            "/cards",
            params={
                "q": query,
                "pageSize": page_size,
                "page": 1,
            },
        )
        cards = payload.get("data", [])
        if not cards:
            raise PokemonTCGAPIError(f"No cards returned while prewarming set '{set_id}'.")

        self._cache[set_id] = cards
        self._save_persistent_cache()
        self._logger.info(
            "Pokemon TCG cache warmed set_id=%s cached_cards=%s total_cards=%s",
            set_id,
            len(cards),
            total,
        )

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        request_params = params or {}
        attempts = self.max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                response = self._session.get(url, params=request_params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as exc:
                self._logger.warning(
                    "Pokemon TCG API request failed (attempt %s/%s) path=%s params=%s error=%s",
                    attempt,
                    attempts,
                    path,
                    request_params,
                    exc,
                )
                if attempt >= attempts:
                    self._logger.exception(
                        "Pokemon TCG API request exhausted retries path=%s params=%s",
                        path,
                        request_params,
                    )
                    raise PokemonTCGAPIError(str(exc)) from exc
                time.sleep(0.4 * attempt)

    def _fetch_set_cards(self, set_id: str) -> List[Dict[str, Any]]:
        if set_id in self._cache:
            return self._cache[set_id]

        if not set_id:
            raise PokemonTCGAPIError("Missing set_id for Pokemon pack pull.")

        all_cards: List[Dict[str, Any]] = []
        page = 1
        page_size = 250
        query = f"set.id:{set_id}"

        while True:
            payload = self._get(
                "/cards",
                params={
                    "q": query,
                    "pageSize": page_size,
                    "page": page,
                },
            )
            cards = payload.get("data", [])
            if not cards:
                break
            all_cards.extend(cards)

            total_count = int(payload.get("totalCount", len(all_cards)))
            if len(all_cards) >= total_count:
                break
            page += 1

        if not all_cards:
            self._logger.error("Pokemon TCG API returned no cards for set_id=%s", set_id)
            raise PokemonTCGAPIError(f"No cards found for set '{set_id}'.")

        self._cache[set_id] = all_cards
        self._save_persistent_cache()
        return all_cards

    def _count_query(self, query: str) -> int:
        cached = self._count_cache.get(query)
        if cached is not None:
            return cached

        payload = self._get(
            "/cards",
            params={
                "q": query,
                "pageSize": 1,
                "page": 1,
            },
        )
        total = int(payload.get("totalCount", 0))
        self._count_cache[query] = total
        return total

    def _random_card_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        total = self._count_query(query)
        if total <= 0:
            return None

        page = random.randint(1, total)
        payload = self._get(
            "/cards",
            params={
                "q": query,
                "pageSize": 1,
                "page": page,
            },
        )
        cards = payload.get("data", [])
        if not cards:
            return None
        return cards[0]

    def _fetch_random_good_card(self, set_id: str) -> Optional[Dict[str, Any]]:
        # Prioritize higher-value rarity pools first.
        good_queries = [
            f'set.id:{set_id} rarity:"Hyper Rare"',
            f'set.id:{set_id} rarity:"Ultra Rare"',
            f'set.id:{set_id} rarity:"Secret Rare"',
            f'set.id:{set_id} rarity:"Illustration Rare"',
            f'set.id:{set_id} rarity:"Special Illustration Rare"',
        ]

        for query in good_queries:
            card = self._random_card_from_query(query)
            if card:
                return card
        return None

    @staticmethod
    def _card_price(card: Dict[str, Any]) -> float:
        cardmarket = card.get("cardmarket", {})
        cm_prices = cardmarket.get("prices", {}) if isinstance(cardmarket, dict) else {}

        for key in ("averageSellPrice", "trendPrice", "avg30", "avg7"):
            value = cm_prices.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)

        tcgplayer = card.get("tcgplayer", {})
        tcg_prices = tcgplayer.get("prices", {}) if isinstance(tcgplayer, dict) else {}
        for print_type in ("holofoil", "normal", "reverseHolofoil"):
            block = tcg_prices.get(print_type, {})
            if not isinstance(block, dict):
                continue
            for key in ("market", "mid", "low"):
                value = block.get(key)
                if isinstance(value, (int, float)) and value > 0:
                    return float(value)

        return 1.0

    @staticmethod
    def _is_good_card(card: Dict[str, Any]) -> bool:
        rarity = (card.get("rarity") or "").lower()
        good_markers = (
            "secret",
            "ultra",
            "hyper",
            "special illustration",
            "illustration rare",
            "gold",
        )
        return any(marker in rarity for marker in good_markers)

    def pull_pack_card(self, set_id: str, good_pull_chance: float = 0.05) -> Dict[str, Any]:
        if not set_id:
            raise PokemonTCGAPIError("Missing set_id for Pokemon pack pull.")

        cached_cards = self._cache.get(set_id, [])
        if cached_cards:
            should_pull_good = random.random() < max(0.0, min(1.0, good_pull_chance))
            if should_pull_good:
                cached_good = [card for card in cached_cards if self._is_good_card(card)]
                if cached_good:
                    card = random.choice(cached_good)
                else:
                    card = random.choice(cached_cards)
            else:
                card = random.choice(cached_cards)

            good_hit = self._is_good_card(card)
            set_data = card.get("set", {}) if isinstance(card.get("set"), dict) else {}
            self._logger.info(
                "Pokemon TCG pull (cache hit) set_id=%s good_roll=%s good_hit=%s card=%s",
                set_id,
                should_pull_good,
                good_hit,
                card.get("name", "Unknown Card"),
            )
            return {
                "name": card.get("name", "Unknown Card"),
                "rarity": card.get("rarity", "Unknown"),
                "set_name": set_data.get("name", set_id),
                "price": round(self._card_price(card), 2),
                "good_hit": good_hit,
            }

        base_query = f"set.id:{set_id}"
        should_pull_good = random.random() < max(0.0, min(1.0, good_pull_chance))
        card = None
        good_hit = False

        if should_pull_good:
            card = self._fetch_random_good_card(set_id)
            good_hit = card is not None

        if not card:
            card = self._random_card_from_query(base_query)
            if not card:
                raise PokemonTCGAPIError(f"No cards found for set '{set_id}'.")
            good_hit = self._is_good_card(card)

        self._logger.info(
            "Pokemon TCG pull set_id=%s good_roll=%s good_hit=%s card=%s",
            set_id,
            should_pull_good,
            good_hit,
            card.get("name", "Unknown Card"),
        )

        set_data = card.get("set", {}) if isinstance(card.get("set"), dict) else {}
        return {
            "name": card.get("name", "Unknown Card"),
            "rarity": card.get("rarity", "Unknown"),
            "set_name": set_data.get("name", set_id),
            "price": round(self._card_price(card), 2),
            "good_hit": good_hit,
        }

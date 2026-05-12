import os
import random
import json
import sys
import logging
import time
from thefuzz import process, fuzz

from util.cs2_case_api import CS2CaseAPIError, CS2CaseClient
from util.database import DatabaseConnection
from util.config import get_config_path
from util.pokemon_tcg_api import PokemonTCGAPIError, PokemonTCGClient
from util.module_registry import module_registry
from modules.economy import Economy

class Inventory:
    load_after = ["economy"]  # Load after the economy module
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        appdata_dir = os.path.dirname(get_config_path())
        cases_path = os.path.join(appdata_dir, "cases.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "cases.json")
        try:
            with open(cases_path, mode="r", encoding="utf-8") as file:
                self.cases = json.load(file)
        except Exception as e:
            raise Exception(f"Error loading cases: {e}")
        self.economy: Economy = module_registry.get_module("economy")
        self.pokemon_tcg = PokemonTCGClient(api_key=os.getenv("POKEMONTCG_API_KEY"))
        self.cs2_case_api = CS2CaseClient()
        self._ensure_pokedex_table()

        # Warm Pokemon set cache on startup so @open is usually instant.
        pokemon_set_ids = [
            case.get("set_id")
            for case in self.cases
            if case.get("source") == "pokemon_tcg_api" and case.get("set_id")
        ]
        if pokemon_set_ids:
            self.pokemon_tcg.prewarm_sets(pokemon_set_ids)

        cs2_case_names = [
            case.get("api_case_name", case.get("name"))
            for case in self.cases
            if case.get("source") == "cs2_case_api"
        ]
        if cs2_case_names:
            self.cs2_case_api.prewarm_cases(cs2_case_names)

    def _ensure_pokedex_table(self):
        """Ensure pokedex discovery table exists."""
        with DatabaseConnection() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_pokedex (
                    user_id TEXT NOT NULL,
                    card_name TEXT NOT NULL,
                    set_id TEXT NOT NULL,
                    set_name TEXT NOT NULL,
                    region TEXT NOT NULL DEFAULT 'Unknown',
                    pulls INTEGER NOT NULL DEFAULT 1,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, card_name, set_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_pokedex_user_region
                ON user_pokedex(user_id, region)
                """
            )

    def record_pokedex_discovery(self, user_id: str, card_name: str, set_id: str, set_name: str, region: str = "Unknown") -> None:
        """Record a pulled Pokemon card discovery for the player's pokedex."""
        with DatabaseConnection() as cursor:
            cursor.execute(
                """
                INSERT INTO user_pokedex (user_id, card_name, set_id, set_name, region)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, card_name, set_id)
                DO UPDATE SET
                    pulls = user_pokedex.pulls + 1,
                    last_seen_at = CURRENT_TIMESTAMP,
                    set_name = EXCLUDED.set_name,
                    region = EXCLUDED.region
                """,
                (user_id, card_name, set_id, set_name, region or "Unknown"),
            )

    def get_pokedex_counts_by_region(self, user_id: str):
        """Return discovered unique card counts grouped by region for a user."""
        with DatabaseConnection() as cursor:
            cursor.execute(
                """
                SELECT region, COUNT(*) AS discovered
                FROM user_pokedex
                WHERE user_id = %s
                GROUP BY region
                ORDER BY region ASC
                """,
                (user_id,),
            )
            return cursor.fetchall()

    def get_pokedex_total_discovered(self, user_id: str) -> int:
        """Return total unique discovered cards for a user."""
        with DatabaseConnection() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM user_pokedex
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def add_item(self, user_id, item_name, item_data, quantity=1):
        """Add an item to the user's inventory."""
        item_data = item_data if isinstance(item_data, str) else json.dumps(item_data)
        # replace any escape characters in item_data
        item_data = item_data.replace("\\\\", "\\").replace("\\'", "'")
        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO user_inventory (user_id, item_name, item_data, quantity)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = user_inventory.quantity + %s
            """, (user_id, item_name, item_data, quantity, quantity))
        return f"Added {quantity} x {item_name} ({item_data}) to {user_id}'s inventory."

    def remove_item(self, user_id, item_name, quantity=1):
        """Remove an item from the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT quantity FROM user_inventory
                WHERE user_id = %s AND item_name ILIKE %s
            """, (user_id, item_name))
            result = cursor.fetchone()
            if not result or result[0] < quantity:
                return f"Not enough {item_name} in inventory to remove."
            
            cursor.execute("""
                UPDATE user_inventory
                SET quantity = quantity - %s
                WHERE user_id = %s AND item_name = %s
            """, (quantity, user_id, item_name))
            cursor.execute("""
                DELETE FROM user_inventory
                WHERE user_id = %s AND item_name = %s AND quantity <= 0
            """, (user_id, item_name))
        return f"Removed {quantity} x {item_name} from {user_id}'s inventory."

    def get_item_by_type(self, playername, item_type):
        """Get items of a specific type from the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT item_name, item_data, quantity FROM user_inventory
                WHERE user_id = %s
            """, (playername,))
            items = cursor.fetchall()
        if not items:
            return None
        found_items = []
        for item in items:
            item_name = item[0]
            item_data = json.loads(item[1])
            quantity = item[2]
            item_type_value = item_data.get("type")
            if item_type_value and item_type_value.lower() == item_type.lower():
                found_items.append((item_name, item_data, quantity))

        if not found_items:
            return None
        return found_items

    def list_inventory(self, user_id):
        """List all items in the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT item_name, item_data, quantity FROM user_inventory
                WHERE user_id = %s
            """, (user_id,))
            items = cursor.fetchall()
        if not items:
            return None
        return [{'name': item[0], 'data': item[1], 'quantity': item[2]} for item in items]

    def open_case(self, user_id, case_name, t=None):
        """Open a case and add a random item to the user's inventory."""
        valid_cases = [case["name"] for case in self.cases]
        valid_case_lookup = {name.lower(): name for name in valid_cases}
        alias_lookup = {}
        for case in self.cases:
            canonical_name = case.get("name")
            for alias in case.get("aliases", []):
                if isinstance(alias, str) and alias.strip():
                    alias_lookup[alias.strip().lower()] = canonical_name

        if case_name:
            user_inv = self.list_inventory(user_id)
            if not user_inv:
                return self._translate(
                    t,
                    "commands.inventory.empty",
                    "Rummaging through your inventory, you find nothing but dust.",
                )

            requested_name = case_name.strip()
            normalized_requested = requested_name.lower()
            canonical_case_name = valid_case_lookup.get(normalized_requested)

            if not canonical_case_name:
                canonical_case_name = alias_lookup.get(normalized_requested)

            if not canonical_case_name:
                partial_match = next(
                    (
                        name
                        for name in valid_cases
                        if normalized_requested in name.lower()
                    ),
                    None,
                )
                canonical_case_name = partial_match

            if not canonical_case_name and alias_lookup:
                partial_alias_match = next(
                    (
                        alias_lookup[alias]
                        for alias in alias_lookup
                        if normalized_requested in alias
                    ),
                    None,
                )
                canonical_case_name = partial_alias_match

            if not canonical_case_name:
                candidates = list(valid_case_lookup.keys()) + list(alias_lookup.keys())
                best_match = process.extractOne(normalized_requested, candidates, scorer=fuzz.ratio)
                if best_match and best_match[1] >= 75:
                    matched_key = best_match[0]
                    canonical_case_name = valid_case_lookup.get(matched_key) or alias_lookup.get(matched_key)

            # check if has case
            if not canonical_case_name:
                return self._translate(
                    t,
                    "commands.inventory.open.no_case_named",
                    "You don't have a {case_name} to open.",
                    case_name=requested_name,
                )
            
            if not any(item["name"].lower() == canonical_case_name.lower() for item in user_inv):
                return self._translate(
                    t,
                    "commands.inventory.open.no_case_named",
                    "You don't have a {case_name} to open.",
                    case_name=canonical_case_name,
                )
            
            # open the case
            # get first case whose ["name"] matches case_name
            case = next((case for case in self.cases if case["name"] == canonical_case_name), None)

            if case and case.get("source") == "cs2_case_api":
                pull_start = time.time()
                api_case_name = case.get("api_case_name", canonical_case_name)
                try:
                    pull = self.cs2_case_api.pull_case_item(
                        api_case_name,
                        knife_pull_chance=float(case.get("knife_pull_chance", 0.0025)),
                    )
                except (ValueError, CS2CaseAPIError):
                    elapsed = time.time() - pull_start
                    self.logger.exception(
                        "CS2 case open failed user=%s case=%s api_case=%s elapsed=%.3fs",
                        user_id,
                        canonical_case_name,
                        api_case_name,
                        elapsed,
                    )
                    return self._translate(
                        t,
                        "commands.inventory.open.cs_api_error",
                        "Couldn't reach case data service right now. Try opening again in a bit.",
                    )

                self.remove_item(user_id, canonical_case_name, 1)
                self.economy.add_balance(user_id, pull["price"])
                elapsed = time.time() - pull_start
                self.logger.info(
                    "CS2 case opened user=%s case=%s item=%s rarity=%s price=%s knife_hit=%s elapsed=%.3fs",
                    user_id,
                    canonical_case_name,
                    pull["name"],
                    pull["rarity"],
                    pull["price"],
                    pull.get("knife_hit", False),
                    elapsed,
                )

                result_text = self._translate(
                    t,
                    "commands.inventory.open.opened_cs_case",
                    "You opened {case_name} and pulled {item_name} ({rarity}) worth ${price:.2f}!",
                    case_name=canonical_case_name,
                    item_name=pull["name"],
                    rarity=pull["rarity"],
                    price=pull["price"],
                )
                if pull.get("knife_hit"):
                    result_text += " " + self._translate(
                        t,
                        "commands.inventory.open.knife_hit",
                        "KNIFE HIT!",
                    )
                return result_text

            if case and case.get("source") == "pokemon_tcg_api":
                pull_start = time.time()
                try:
                    pull = self.pokemon_tcg.pull_pack_card(
                        case.get("set_id", ""),
                        good_pull_chance=float(case.get("good_pull_chance", 0.05)),
                    )
                except (ValueError, PokemonTCGAPIError) as exc:
                    elapsed = time.time() - pull_start
                    self.logger.exception(
                        "Pokemon pack open failed user=%s case=%s set_id=%s elapsed=%.3fs",
                        user_id,
                        canonical_case_name,
                        case.get("set_id", ""),
                        elapsed,
                    )
                    return self._translate(
                        t,
                        "commands.inventory.open.api_error",
                        "Couldn't reach card data service right now. Try opening again in a bit.",
                    )

                self.remove_item(user_id, canonical_case_name, 1)
                self.economy.add_balance(user_id, pull["price"])
                self.record_pokedex_discovery(
                    user_id,
                    pull["name"],
                    case.get("set_id", "unknown"),
                    pull["set_name"],
                    case.get("region", "Unknown"),
                )
                elapsed = time.time() - pull_start
                self.logger.info(
                    "Pokemon pack opened user=%s case=%s card=%s rarity=%s set=%s price=%s good_hit=%s elapsed=%.3fs",
                    user_id,
                    canonical_case_name,
                    pull["name"],
                    pull["rarity"],
                    pull["set_name"],
                    pull["price"],
                    pull.get("good_hit", False),
                    elapsed,
                )
                result_text = self._translate(
                    t,
                    "commands.inventory.open.opened_pokemon_pack",
                    "You opened {case_name} and pulled {item_name} ({rarity}) from {set_name} worth ${price:.2f}!",
                    case_name=canonical_case_name,
                    item_name=pull["name"],
                    rarity=pull["rarity"],
                    set_name=pull["set_name"],
                    price=pull["price"],
                )
                if pull.get("good_hit"):
                    result_text += " " + self._translate(
                        t,
                        "commands.inventory.open.good_card_hit",
                        "GOOD CARD HIT!",
                    )
                return result_text

            # milspec, restricted, classified, covert, and special
            rarities = [.7995, .15, .042, .006, .0025]

            rarity = random.choices(
                ["mil-spec", "restricted", "classified", "covert", "exceedingly-rare"],
                weights=rarities,
                k=1
            )[0]

            item = random.choice(case["items"][rarity])

            # remove case from inventory
            self.remove_item(user_id, canonical_case_name, 1)
            
            self.economy.add_balance(user_id, item['price'])
            return self._translate(
                t,
                "commands.inventory.open.opened_case",
                "You opened a {case_name} and got a {item_name} worth {price}! You sell it and pocket the change.",
                case_name=canonical_case_name,
                item_name=item['name'],
                price=item['price'],
            )

        else:
            # open the first case in the inventory
            user_inv = self.list_inventory(user_id)
            if not user_inv:
                return self._translate(
                    t,
                    "commands.inventory.empty",
                    "Rummaging through your inventory, you find nothing but dust.",
                )
            
            # Find the first openable case/pack from inventory.
            case_name = next((item['name'] for item in user_inv if item['name'] in valid_cases), None)

            if not case_name:
                return None
            return self.open_case(user_id, case_name, t=t)

    def get_item_by_name(self, user_id, item_name):
        """Get an item by its name from the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT item_name, item_data, quantity FROM user_inventory
                WHERE user_id = %s AND item_name ILIKE %s
            """, (user_id, item_name))
            result = cursor.fetchone()
        if not result:
            return None
        return {
            "name": result[0],
            "data": json.loads(result[1]),
            "quantity": result[2]
        }

    def get_item_by_name_fuzzy(self, user_id, item_name):
        """Get an item by its name from the user's inventory using fuzzy matching."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT item_name FROM user_inventory
                WHERE user_id = %s
            """, (user_id,))
            items = cursor.fetchall()
        
        if not items:
            return None
        
        item_names = [item[0] for item in items]
        best_match = process.extractOne(item_name, item_names, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= 80:
            return self.get_item_by_name(user_id, best_match[0])
        return None

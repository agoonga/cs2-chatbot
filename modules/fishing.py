import random
import json
import os
import sys
from thefuzz import process, fuzz

from util.database import DatabaseConnection
from util.config import get_config_path
from util.module_registry import module_registry
from modules.inventory import Inventory as InventoryModule
from modules.status_effects import StatusEffects as StatusEffectsModule

class Fishing:
    load_after = ["inventory", "economy"]  # Load after the inventory and economy modules
    def __init__(self):
        self.fish_data = self.load_fish_data()
        self.inventory: InventoryModule = module_registry.get_module("inventory")  # Retrieve the Inventory module from the module registry
        self.status_effects: StatusEffectsModule = module_registry.get_module("status_effects")  # Retrieve the StatusEffects module from the module registry
        self.economy = module_registry.get_module("economy")

    def _translate(self, t, key, default_text, **kwargs):
        """Translate via callback when available, otherwise use default text."""
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def load_fish_data(self):
        """Load fish data from a JSON file."""
        appdata_dir = os.path.dirname(get_config_path())  # Get the app data directory
        fish_json_path = os.path.join(appdata_dir, "fish.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "fish.json")
        try:
            with open(fish_json_path, mode='r', encoding='utf-8') as file:
                fish_data = json.load(file)
                for item in fish_data:
                    if item.get("type") != "fish":
                        continue
                    if item.get("description"):
                        continue
                    fish_name = item.get("name", "fish")
                    if "crab" in fish_name.lower():
                        item["description"] = f"You crack into the {fish_name}, buttery and rich with a salty ocean finish."
                    else:
                        item["description"] = f"You eat the {fish_name}. Fresh catch, solid meal."
                return fish_data
        except FileNotFoundError:
            return []

    def calculate_miss_chance(self, playername):
        """
        Calculate the chance of missing a fish based on the player's stats.
        """
        miss_chance = 0.3  # Base miss chance

        # Check player's inventory for fishing gear
        rod = self.inventory.get_item_by_type(playername, "rod")
        if rod:
            # Assuming the rod has a miss chance attribute
            rod = rod[0][1]
            attributes = rod.get("attributes", {})
            if "fish_none_rate_multiplier" in attributes:
                miss_chance = miss_chance * attributes["fish_none_rate_multiplier"]
        
        # Check player's status effects
        effects = self.status_effects.get_effects(playername)
        for effect in effects:
            if effect.get("module_id") == "fishing" and effect.get("effect_id").startswith("miss_rate"):
                miss_chance = miss_chance * effect.get("mult", 1)
        
        return miss_chance
            
    def calculate_sack_size(self, playername):
        """
        Calculate the sack size based on the player's stats.
        """
        # Check player's inventory for fishing gear
        sack = self.inventory.get_item_by_type(playername, "sack")
        if sack:
            sack = sack[0][1]
            # Assuming the sack has a size attribute
            attributes = sack.get("attributes", {})
            if "fish_capacity" in attributes:
                return attributes["fish_capacity"]
        return 5 # Default sack size if no sack is found
        
    def get_minimum_rarity(self, playername):
        """
        Get the minimum rarity of fish that can be caught based on the player's stats.
        """
        # Check player's inventory for fishing gear
        rod = self.inventory.get_item_by_type(playername, "rod")
        if rod:
            # Assuming the rod has a rarity attribute
            rod = rod[0][1]
            attributes = rod.get("attributes", {})
            if "fish_minimum_rarity" in attributes:
                return attributes["fish_minimum_rarity"]
        return "Common"
    
    def fish(self, user_id, t=None):
        """Simulate fishing and store the result in the database or inventory."""
        if not self.fish_data:
            return None

        # Check the current number of fish in the user's sack
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM caught_fish
                WHERE user_id = %s
            """, (user_id,))
            fish_count = cursor.fetchone()

        # Convert fish_count to an integer
        fish_count = int(fish_count[0]) if fish_count else 0

        # Enforce fish limit
        sack_size = self.calculate_sack_size(user_id)  # Get the sack size
        if sack_size > 0 and fish_count >= sack_size:
            return {
                "type": "error",
                "message": self._translate(
                    t,
                    "commands.fishing.sack_limit_reached",
                    "Your sack can only hold {sack_size} fish.",
                    sack_size=sack_size,
                ),
            }

        # Randomly select a fish or item based on catch rate
        rarities = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"] # Rarities increasing in value
        minimum_rarity = self.get_minimum_rarity(user_id)  # Get the minimum rarity
        miss_chance = self.calculate_miss_chance(user_id)  # Calculate the miss chance

        # Check if the player has a bait set
        bait = self.get_bait(user_id)
        if bait:
            # Remove the bait from the sack
            self.remove_fish_from_sack(user_id, bait["id"])
            # Remove the bait from the database
            with DatabaseConnection() as cursor:
                cursor.execute("""
                    DELETE FROM caught_fish
                    WHERE id = %s
                """, (bait["id"],))

            # Check the rarity of the bait
            bait_rarity = bait.get("rarity", "Common")
            bait_rarity_index = rarities.index(bait_rarity)
            minimum_rarity_index = rarities.index(minimum_rarity)
            
            # If the bait rarity is higher than the minimum rarity, set the minimum rarity to the bait's rarity
            if bait_rarity_index > minimum_rarity_index:
                minimum_rarity = bait_rarity

            # Increase the miss chance
            miss_chance = 0.1 * (bait_rarity_index - minimum_rarity_index) + miss_chance
        
        # get fish around
        fish_around = []
        minimum_rarity_index = rarities.index(minimum_rarity)
        for item in self.fish_data:
            if item.get("type") == "item":
                item_copy = item.copy()
                item_rarity = item_copy.get("rarity", "Common")
                item_rarity_index = rarities.index(item_rarity) if item_rarity in rarities else 0
                if item_rarity_index < minimum_rarity_index:
                    penalty_steps = minimum_rarity_index - item_rarity_index
                    item_copy["catch_rate"] *= 0.5 ** penalty_steps
                fish_around.append(item_copy)
                continue

            if item["rarity"] == minimum_rarity or item["rarity"] in rarities[rarities.index(minimum_rarity):]:
                fish_around.append(item.copy())
        
        # alter catch rate based on status effects
        effects = self.status_effects.get_effects(user_id)
        for effect in effects:
            # legendary_rate effect
            if effect.get("module_id") == "fishing" and effect.get("effect_id").startswith("legendary_rate"):
                for item in fish_around:
                    if item["rarity"] == "Legendary":
                        item["catch_rate"] *= effect.get("mult", 1)
            # catch_rate effect
            if effect.get("module_id") == "fishing" and effect.get("effect_id").startswith("catch_rate"):
                for item in fish_around:
                    item["catch_rate"] *= effect.get("mult", 1)
            # item_rate / case_rate effect
            if effect.get("module_id") == "fishing" and (
                effect.get("effect_id").startswith("item_rate") or
                effect.get("effect_id").startswith("case_rate")
            ):
                for item in fish_around:
                    if item["type"] == "item":
                        item["catch_rate"] *= effect.get("mult", 1)
                    
        
        fish_catch_rate = sum(item["catch_rate"] for item in fish_around)  # Calculate the total catch rate for the filtered fish
        total_catch_rate = fish_catch_rate + (fish_catch_rate *  miss_chance)  # Adjust the total catch rate based on miss chance
        random_roll = random.uniform(0, total_catch_rate)
        cumulative_rate = 0

        for item in fish_around:
            cumulative_rate += item["catch_rate"]
            if random_roll <= cumulative_rate:
                if item["type"] == "fish":
                    # Randomize the weight of the fish
                    weight = round(random.uniform(item["min_weight"], item["max_weight"]), 2)
                    # Calculate the price based on the weight and price multiplier
                    price = weight * item["price_multiplier"]
                    # price status effect
                    for effect in effects:
                        if effect.get("module_id") == "fishing" and effect.get("effect_id").startswith("price"):
                            price *= effect.get("mult", 1)
                    price = round(price, 2)

                    if self.is_autosell_enabled(user_id, item["name"]):
                        new_balance = self.economy.add_balance(user_id, float(price))
                        return {
                            "name": item["name"],
                            "type": "autosold_fish",
                            "weight": weight,
                            "price": price,
                            "balance": new_balance
                        }

                    # Add the fish to the database
                    self.add_fish_to_db(user_id, item["name"], weight, price)
                    return {"name": item["name"], "type": "fish", "weight": weight, "price": price}
                elif item["type"] == "item":
                    # Add the item to the inventory
                    self.inventory.add_item(user_id, item["name"], item, 1)
                    return {"name": item["name"], "type": "item", "message": f"You found a {item['name']}!"}

    def add_fish_to_db(self, user_id, name, weight, price):
        """Add a caught fish to the database."""
        with DatabaseConnection() as cursor:

        # Add the new fish to the database
            cursor.execute("""
                INSERT INTO caught_fish (user_id, name, weight, price)
                VALUES (%s, %s, %s, %s)
            """, (user_id, name, weight, price))
        return f"You caught a {name} weighing {weight} lbs worth ${price}!"

    def _get_all_fish_names(self):
        return [item["name"] for item in self.fish_data if item.get("type") == "fish"]

    def resolve_fish_name(self, fish_name):
        """Resolve a fish name to canonical fish data name using exact then fuzzy matching."""
        if not fish_name:
            return None

        fish_name = fish_name.strip()
        fish_names = self._get_all_fish_names()
        if not fish_names:
            return None

        exact = next((name for name in fish_names if name.lower() == fish_name.lower()), None)
        if exact:
            return exact

        best_match = process.extractOne(fish_name, fish_names, scorer=fuzz.ratio)
        if best_match and best_match[1] >= 80:
            return best_match[0]

        return None

    def add_autosell_fish(self, user_id, fish_name):
        """Add a fish to a user's autosell list and immediately sell matching fish in sack."""
        resolved_fish_name = self.resolve_fish_name(fish_name)
        if not resolved_fish_name:
            return False, f"'{fish_name}' is not a valid fish. Only fish can be autosold."

        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO autosell_fish (user_id, fish_name)
                VALUES (%s, %s)
                ON CONFLICT (user_id, fish_name) DO NOTHING
            """, (user_id, resolved_fish_name))
            added = cursor.rowcount > 0

        sold_count, sold_total, _ = self.sell_matching_fish_in_sack(user_id, resolved_fish_name)

        if added and sold_count > 0:
            return True, f"Enabled autosell for {resolved_fish_name}. Sold {sold_count} for ${sold_total:.2f}."
        if added:
            return True, f"Enabled autosell for {resolved_fish_name}."
        if sold_count > 0:
            return True, f"{resolved_fish_name} is already autosold. Sold {sold_count} for ${sold_total:.2f}."

        return True, f"{resolved_fish_name} is already autosold."

    def remove_autosell_fish(self, user_id, fish_name):
        """Remove a fish from a user's autosell list."""
        resolved_fish_name = self.resolve_fish_name(fish_name)
        if not resolved_fish_name:
            return False, f"'{fish_name}' is not a valid fish."

        with DatabaseConnection() as cursor:
            cursor.execute("""
                DELETE FROM autosell_fish
                WHERE user_id = %s AND fish_name = %s
            """, (user_id, resolved_fish_name))
            removed = cursor.rowcount > 0

        if not removed:
            return False, f"{resolved_fish_name} is not in your autosell list."

        return True, f"Disabled autosell for {resolved_fish_name}."

    def list_autosell_fish(self, user_id):
        """List autosell fish for a user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT fish_name
                FROM autosell_fish
                WHERE user_id = %s
                ORDER BY fish_name ASC
            """, (user_id,))
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    def clear_autosell_fish(self, user_id):
        """Clear all autosell fish preferences for a user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                DELETE FROM autosell_fish
                WHERE user_id = %s
            """, (user_id,))
            removed_count = cursor.rowcount

        if removed_count <= 0:
            return False, "Your autosell list is already empty."

        return True, f"Cleared autosell list ({removed_count} removed)."

    def is_autosell_enabled(self, user_id, fish_name):
        """Check whether autosell is enabled for a fish for this user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT 1
                FROM autosell_fish
                WHERE user_id = %s AND LOWER(fish_name) = LOWER(%s)
                LIMIT 1
            """, (user_id, fish_name))
            return cursor.fetchone() is not None

    def sell_matching_fish_in_sack(self, user_id, fish_name):
        """Sell all non-bait fish matching a specific name in the user's sack."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT price
                FROM caught_fish
                WHERE user_id = %s AND LOWER(name) = LOWER(%s) AND bait = 0
            """, (user_id, fish_name))
            rows = cursor.fetchall()

            if not rows:
                return 0, 0.0, self.economy.get_balance(user_id)

            total_earnings = float(sum(float(row[0]) for row in rows))
            sold_count = len(rows)

            cursor.execute("""
                DELETE FROM caught_fish
                WHERE user_id = %s AND LOWER(name) = LOWER(%s) AND bait = 0
            """, (user_id, fish_name))

        new_balance = self.economy.add_balance(user_id, total_earnings)
        return sold_count, total_earnings, new_balance

    def get_sack(self, user_id):
        """Retrieve all fish caught by the user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, name, weight, price, bait
                FROM caught_fish
                WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchall()
        return [{"id": row[0], "name": row[1], "weight": row[2], "price": row[3], "bait": row[4]} for row in result]

    def clear_sack(self, user_id):
        """Remove all fish caught by the user."""
        with DatabaseConnection() as cursor:
            cursor.execute("DELETE FROM caught_fish WHERE user_id = %s", (user_id,))
    def list_fish(self):
        """List all available fish and items."""
        return self.fish_data

    def eat(self, user_id, name=None, t=None):
        """
        Eat the first fish matching the given name from the user's sack, or the first fish if no name is provided.

        :param user_id: The ID of the user.
        :param name: The name of the fish to eat (optional).
        :return: A description of the fish or an error message if the fish is not found.
        """
        with DatabaseConnection() as cursor:

            if name:
                # Sanitize the name input
                name = name.strip()

                # Retrieve the first fish matching the name (case-insensitive) from the database
                cursor.execute("""
                    SELECT id, name
                    FROM caught_fish
                    WHERE user_id = %s AND LOWER(name) = LOWER(%s)
                    LIMIT 1
                """, (user_id, name))
            else:
                # Retrieve the first fish in the sack if no name is provided
                cursor.execute("""
                    SELECT id, name
                    FROM caught_fish
                    WHERE user_id = %s
                    LIMIT 1
                """, (user_id,))
            
            fish = cursor.fetchone()

            if not fish:
                if not name:
                    return self._translate(t, "commands.fishing.eat_sack_empty", "Your sack is empty.")
                return self._translate(
                    t,
                    "commands.fishing.eat_fish_not_found",
                    "There were no '{name}' found in your sack.",
                    name=name,
                )

            fish_id, name = fish

            # Remove the fish from the database
            cursor.execute("""
                DELETE FROM caught_fish
                WHERE id = %s
            """, (fish_id,))

        # Retrieve the fish description from the fish data
        for fish_data in self.fish_data:
            if fish_data["name"].lower() == name.lower():
                return fish_data.get("description", self._translate(t, "commands.fishing.ate_fish", "You ate the fish."))

        return self._translate(t, "commands.fishing.ate_fish", "You ate the fish.")

    def sell_fish(self, user_id, name=None, t=None):
        """
        Sell the first fish matching the given name from the user's sack, or sell all fish if 'all' is provided.

        :param user_id: The ID of the user.
        :param name: The name of the fish to sell, or 'all' to sell all fish.
        :return: The total earnings or an error message if no fish is found.
        """

        with DatabaseConnection() as cursor:

            if name and name.strip().lower() == "all":
                # Sell all fish in the sack
                cursor.execute("""
                    SELECT price
                    FROM caught_fish
                    WHERE user_id = %s
                    AND bait = 0
                """, (user_id,))
                fish_prices = cursor.fetchall()

                if not fish_prices:
                    return self._translate(
                        t,
                        "commands.fishing.sell_all_sack_empty",
                        "Your sack is empty. You have no fish to sell.",
                    )

                total_earnings = float(sum(price[0] for price in fish_prices))

                # Remove all fish from the database
                cursor.execute("""
                    DELETE FROM caught_fish
                    WHERE user_id = %s
                    AND bait = 0
                """, (user_id,))
                # Add the earnings to the user's balance
                new_balance = self.economy.add_balance(user_id, total_earnings)

                return self._translate(
                    t,
                    "commands.fishing.sold_all_fish",
                    "You sold all your fish for a total of ${total_earnings:.2f}! Your new balance is ${new_balance:.2f}.",
                    total_earnings=total_earnings,
                    new_balance=new_balance,
                )
            else:
                # Sell the first fish in the sack or the first matching fish
                if name:
                    # Sanitize the name input
                    name = name.strip()

                    # Retrieve the first fish matching the name (case-insensitive) from the database
                    cursor.execute("""
                        SELECT id, name, price
                        FROM caught_fish
                        WHERE user_id = %s AND LOWER(name) = LOWER(%s)
                        LIMIT 1
                    """, (user_id, name))
                else:
                    # Retrieve the first fish in the sack if no name is provided
                    cursor.execute("""
                        SELECT id, name, price
                        FROM caught_fish
                        WHERE user_id = %s
                        LIMIT 1
                    """, (user_id,))

                fish = cursor.fetchone()

                if not fish:
                    if not name:
                        return self._translate(
                            t,
                            "commands.fishing.sell_sack_empty",
                            "Your sack is empty.",
                        )
                    return self._translate(
                        t,
                        "commands.fishing.sell_fish_not_found",
                        "There were no '{name}' found in your sack.",
                        name=name,
                    )

                fish_id, name, price = fish

                # Remove the fish from the database
                cursor.execute("""
                    DELETE FROM caught_fish
                    WHERE id = %s
                """, (fish_id,))
                # Add the earnings to the user's balance
                new_balance = self.economy.add_balance(user_id, float(price))
                
                return self._translate(
                    t,
                    "commands.fishing.sold_single_fish",
                    "You sold a {name} for ${price:.2f}! Your new balance is ${new_balance:.2f}.",
                    name=name,
                    price=price,
                    new_balance=new_balance,
                )

    def bait(self, playername, bait_name, t=None):
        """
        Use a specific fish to bait the next catch.
        If no fish is provided, it will use the cheapest fish in the sack.

        :param playername: The name of the player.
        :param bait_name: The name of the bait to add.
        :return: A message indicating the result of the operation.
        """
        # Check if the player has any fish in their sack
        sack = self.get_sack(playername)
        if not sack:
            return self._translate(
                t,
                "commands.fishing.bait_no_fish_to_use",
                "Your sack is empty. You have no fish to use as bait.",
            )
        
        # If no bait name is provided, use the cheapest fish in the sack
        if not bait_name:
            # Find the cheapest fish in the sack
            cheapest_fish = min(sack, key=lambda x: x["price"])
            bait_id = cheapest_fish["id"]
        else:
            # Sanitize the bait name input
            bait_name = bait_name.strip()

            # Check if the specified fish is in the sack
            for fish in sack:
                if fish["name"].lower() == bait_name.lower():
                    bait_name = fish["name"]
                    bait_id = fish["id"]
                    break
            else:
                return self._translate(
                    t,
                    "commands.fishing.bait_not_found",
                    "There were no '{bait_name}' found in your sack.",
                    bait_name=bait_name,
                )
            
        # Check that there is no bait already set
        bait = self.get_bait(playername)
        if bait:
            # If there is a fish provided that is not the bait fish, set the bait to the provided fish
            if bait["id"] != bait_id:
                # Set the bait to the provided fish
                bait_name = bait["name"]
                bait_id = bait["id"]
                self.set_bait(playername, bait_id)
                return self._translate(
                    t,
                    "commands.fishing.bait_set_next",
                    "You will use a {bait_name} as bait for your next catch.",
                    bait_name=bait_name,
                )

            return self._translate(
                t,
                "commands.fishing.bait_already_set",
                "You already have a bait set: {bait_name}.",
                bait_name=bait['name'],
            )

        # Add the fish to bait for the player
        self.set_bait(playername, bait_id)
        return self._translate(
            t,
            "commands.fishing.bait_set_next",
            "You will use a {bait_name} as bait for your next catch.",
            bait_name=bait_name,
        )
    
    def get_bait(self, playername):
        """
        Get the bait set for the player.

        :param playername: The name of the player.
        :return: The bait set for the player or None if no bait is set.
        """
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM caught_fish
                WHERE user_id = %s AND bait = 1
                LIMIT 1
            """, (playername,))
            bait = cursor.fetchone()
        if bait:
            # Get the corresponding fish data
            fish_data = next((fish for fish in self.fish_data if fish["name"].lower() == bait[1].lower()), None)
            if fish_data:
                return {
                    "id": bait[0],
                    "name": bait[1],
                    "rarity": fish_data.get("rarity", "Common"),
                    "description": fish_data.get("description", "No description available.")
                }
        return None
    
    def set_bait(self, playername, bait_id):
        """
        Set the bait for the player.

        :param playername: The name of the player.
        :param bait_id: The ID of the bait fish.
        """
        with DatabaseConnection() as cursor:

            # Unset any existing bait for the player
            cursor.execute("""
                UPDATE caught_fish
                SET bait = 0
                WHERE user_id = %s AND bait = 1
            """, (playername,))

            # Set the bait for the player
            cursor.execute("""
                UPDATE caught_fish
                SET bait = 1
                WHERE id = %s AND user_id = %s
            """, (bait_id, playername))
        return True

    def remove_fish_from_sack(self, user_id, fish_id):
        """
        Remove a specific fish from the user's sack.

        :param user_id: The ID of the user.
        :param fish_id: The ID of the fish to remove.
        """
        with DatabaseConnection() as cursor:
            cursor.execute("""
                DELETE FROM caught_fish
                WHERE id = %s AND user_id = %s
            """, (fish_id, user_id))
    
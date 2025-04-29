import random
import sqlite3
import json
import os
import sys

from util.config import get_config_path
from util.module_registry import module_registry
from modules.inventory import Inventory as InventoryModule

class Fishing:
    load_after = ["inventory", "economy"]  # Load after the inventory and economy modules
    def __init__(self):
        self.fish_data = self.load_fish_data()
        appdata_dir = os.path.dirname(get_config_path())  # Get the app data directory
        self.db_path = os.path.join(appdata_dir if hasattr(sys, '_MEIPASS') else "db", "fish.db")
        self.initialize_database()
        self.inventory: InventoryModule = module_registry.get_module("inventory")  # Retrieve the Inventory module from the module registry

    def load_fish_data(self):
        """Load fish data from a JSON file."""
        appdata_dir = os.path.dirname(get_config_path())  # Get the app data directory
        fish_json_path = os.path.join(appdata_dir, "fish.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "fish.json")
        try:
            with open(fish_json_path, mode='r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def initialize_database(self):
        """Initialize the SQLite database for storing caught fish."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caught_fish (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                weight REAL NOT NULL,
                price REAL NOT NULL,
                bait INTEGER DEFAULT 0
            )
        """)

        # Create bait column if it doesn't exist
        cursor.execute("""
            PRAGMA table_info(caught_fish)
        """)
        columns = [column[1] for column in cursor.fetchall()]
        if "bait" not in columns:
            cursor.execute("""
                ALTER TABLE caught_fish ADD COLUMN bait INTEGER DEFAULT 0
            """)

        conn.commit()
        conn.close()

    def calculate_miss_chance(self, playername):
        """
        Calculate the chance of missing a fish based on the player's stats.
        """
        # Check player's inventory for fishing gear
        rod = self.inventory.get_item_by_type(playername, "rod")
        if rod:
            # Assuming the rod has a miss chance attribute
            rod = rod[0][1]
            attributes = rod.get("attributes", {})
            if "fish_none_rate_multiplier" in attributes:
                return 0.3 * attributes["fish_none_rate_multiplier"]
        return 0.3  # Default miss chance if no rod is found
            
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
    
    def fish(self, user_id):
        """Simulate fishing and store the result in the database or inventory."""
        if not self.fish_data:
            return None

        # Check the current number of fish in the user's sack
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM caught_fish
            WHERE user_id = ?
        """, (user_id,))
        fish_count = cursor.fetchone()

        # Convert fish_count to an integer
        fish_count = int(fish_count[0]) if fish_count else 0

        # Enforce fish limit
        sack_size = self.calculate_sack_size(user_id)  # Get the sack size
        conn.close()

        if sack_size > 0 and fish_count >= sack_size:
            return {"type": "error", "message": f"Your sack can only hold {sack_size} fish."}

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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM caught_fish
                WHERE id = ?
            """, (bait["id"],))
            conn.commit()
            conn.close()

            # Check the rarity of the bait
            bait_rarity = bait.get("rarity", "Common")
            bait_rarity_index = rarities.index(bait_rarity)
            minimum_rarity_index = rarities.index(minimum_rarity)
            
            # If the bait rarity is higher than the minimum rarity, set the minimum rarity to the bait's rarity
            if bait_rarity_index > minimum_rarity_index:
                minimum_rarity = bait_rarity

            # Increase the miss chance
            miss_chance = 0.1 * (bait_rarity_index - minimum_rarity_index) + miss_chance
        
        fish_around = []
        for item in self.fish_data:
            if item["rarity"] == minimum_rarity or item["rarity"] in rarities[rarities.index(minimum_rarity):]:
                fish_around.append(item)
        
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
                    price = round(weight * item["price_multiplier"], 2)
                    # Add the fish to the database
                    self.add_fish_to_db(user_id, item["name"], weight, price)
                    return {"name": item["name"], "type": "fish", "weight": weight, "price": price}
                elif item["type"] == "item":
                    # Add the item to the inventory
                    self.inventory.add_item(user_id, item["name"], item, 1)
                    return {"name": item["name"], "type": "item", "message": f"You found a {item['name']}!"}

    def add_fish_to_db(self, user_id, name, weight, price):
        """Add a caught fish to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add the new fish to the database
        cursor.execute("""
            INSERT INTO caught_fish (user_id, name, weight, price)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, weight, price))
        conn.commit()
        conn.close()
        return f"You caught a {name} weighing {weight} lbs worth ${price}!"

    def get_sack(self, user_id):
        """Retrieve all fish caught by the user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, weight, price, bait
            FROM caught_fish
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "name": row[1], "weight": row[2], "price": row[3], "bait": row[4]} for row in result]

    def clear_sack(self, user_id):
        """Remove all fish caught by the user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM caught_fish WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def list_fish(self):
        """List all available fish and items."""
        return self.fish_data

    def eat(self, user_id, name=None):
        """
        Eat the first fish matching the given name from the user's sack, or the first fish if no name is provided.

        :param user_id: The ID of the user.
        :param name: The name of the fish to eat (optional).
        :return: A description of the fish or an error message if the fish is not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if name:
            # Sanitize the name input
            name = name.strip()

            # Retrieve the first fish matching the name (case-insensitive) from the database
            cursor.execute("""
                SELECT id, name
                FROM caught_fish
                WHERE user_id = ? AND LOWER(name) = LOWER(?)
                LIMIT 1
            """, (user_id, name))
        else:
            # Retrieve the first fish in the sack if no name is provided
            cursor.execute("""
                SELECT id, name
                FROM caught_fish
                WHERE user_id = ?
                LIMIT 1
            """, (user_id,))
        
        fish = cursor.fetchone()

        if not fish:
            conn.close()
            return "Your sack is empty." if not name else f"There were no '{name}' found in your sack."

        fish_id, name = fish

        # Remove the fish from the database
        cursor.execute("""
            DELETE FROM caught_fish
            WHERE id = ?
        """, (fish_id,))
        conn.commit()
        conn.close()

        # Retrieve the fish description from the fish data
        for fish_data in self.fish_data:
            if fish_data["name"].lower() == name.lower():
                return fish_data.get("description", "You ate the fish.")

        return "You ate the fish."

    def sell_fish(self, user_id, name=None):
        """
        Sell the first fish matching the given name from the user's sack, or sell all fish if 'all' is provided.

        :param user_id: The ID of the user.
        :param name: The name of the fish to sell, or 'all' to sell all fish.
        :return: The total earnings or an error message if no fish is found.
        """

        # Check if the bot has the economy module loaded to its modules
        try:
            economy = module_registry.get_module("economy")
        except ValueError:
            return "Economy module not found."

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if name and name.strip().lower() == "all":
            # Sell all fish in the sack
            cursor.execute("""
                SELECT price
                FROM caught_fish
                WHERE user_id = ?
            """, (user_id,))
            fish_prices = cursor.fetchall()

            if not fish_prices:
                conn.close()
                return "Your sack is empty. You have no fish to sell."

            total_earnings = sum(price[0] for price in fish_prices)

            # Remove all fish from the database
            cursor.execute("""
                DELETE FROM caught_fish
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            conn.close()

            # Add the earnings to the user's balance
            new_balance = economy.add_balance(user_id, total_earnings)

            return f"You sold all your fish for a total of ${total_earnings:.2f}! Your new balance is ${new_balance:.2f}."
        else:
            # Sell the first fish in the sack or the first matching fish
            if name:
                # Sanitize the name input
                name = name.strip()

                # Retrieve the first fish matching the name (case-insensitive) from the database
                cursor.execute("""
                    SELECT id, name, price
                    FROM caught_fish
                    WHERE user_id = ? AND LOWER(name) = LOWER(?)
                    LIMIT 1
                """, (user_id, name))
            else:
                # Retrieve the first fish in the sack if no name is provided
                cursor.execute("""
                    SELECT id, name, price
                    FROM caught_fish
                    WHERE user_id = ?
                    LIMIT 1
                """, (user_id,))

            fish = cursor.fetchone()

            if not fish:
                conn.close()
                return "Your sack is empty." if not name else f"There were no '{name}' found in your sack."

            fish_id, name, price = fish

            # Remove the fish from the database
            cursor.execute("""
                DELETE FROM caught_fish
                WHERE id = ?
            """, (fish_id,))
            conn.commit()
            conn.close()

            # Add the earnings to the user's balance
            new_balance = economy.add_balance(user_id, price)
            
            return f"You sold a {name} for ${price:.2f}! Your new balance is ${new_balance:.2f}."

    def bait(self, playername, bait_name):
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
            return "Your sack is empty. You have no fish to use as bait."
        
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
                return f"There were no '{bait_name}' found in your sack."
            
        # Check that there is no bait already set
        bait = self.get_bait(playername)
        if bait:
            # If there is a fish provided that is not the bait fish, set the bait to the provided fish
            if bait["id"] != bait_id:
                # Set the bait to the provided fish
                bait_name = bait["name"]
                bait_id = bait["id"]
                self.set_bait(playername, bait_id)
                return f"You will use a {bait_name} as bait for your next catch."

            return f"You already have a bait set: {bait['name']}."

        # Add the fish to bait for the player
        self.set_bait(playername, bait_id)
        return f"You will use a {bait_name} as bait for your next catch."
    
    def get_bait(self, playername):
        """
        Get the bait set for the player.

        :param playername: The name of the player.
        :return: The bait set for the player or None if no bait is set.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name
            FROM caught_fish
            WHERE user_id = ? AND bait = 1
            LIMIT 1
        """, (playername,))
        bait = cursor.fetchone()
        conn.close()
        
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Unset any existing bait for the player
        cursor.execute("""
            UPDATE caught_fish
            SET bait = 0
            WHERE user_id = ? AND bait = 1
        """, (playername,))

        # Set the bait for the player
        cursor.execute("""
            UPDATE caught_fish
            SET bait = 1
            WHERE id = ? AND user_id = ?
        """, (bait_id, playername))

        conn.commit()
        conn.close()
        return True

    def remove_fish_from_sack(self, user_id, fish_id):
        """
        Remove a specific fish from the user's sack.

        :param user_id: The ID of the user.
        :param fish_id: The ID of the fish to remove.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM caught_fish
            WHERE id = ? AND user_id = ?
        """, (fish_id, user_id))
        conn.commit()
        conn.close()
    
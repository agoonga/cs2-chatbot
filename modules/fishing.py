import random
import sqlite3
import json
import os
import sys

from util.config import get_config_path
from util.module_registry import module_registry

class Fishing:
    load_after = ["inventory", "economy"]  # Load after the inventory and economy modules
    def __init__(self):
        self.fish_data = self.load_fish_data()
        appdata_dir = os.path.dirname(get_config_path())  # Get the AppData directory
        self.db_path = os.path.join(appdata_dir if hasattr(sys, '_MEIPASS') else "db", "fish.db")
        self.initialize_database()

    def load_fish_data(self):
        """Load fish data from a JSON file."""
        fish_json_path = os.path.join("modules", "data", "fish.json")
        try:
            with open(fish_json_path, mode='r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: {fish_json_path} not found.")
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
                price REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def fish(self, user_id):
        """Simulate fishing and store the result in the database or inventory."""
        if not self.fish_data:
            print("No fish data available.")
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

        print(f"User {user_id} has {fish_count} fish in their sack.")

        # Enforce the limit of 5 fish
        if fish_count >= 5:
            conn.close()
            print(f"User {user_id} has reached the limit of 5 fish.")
            return {"type": "error", "message": "You cannot carry more than 5 fish in your sack."}

        conn.close()

        # Randomly select a fish or item based on catch rate
        total_catch_rate = sum(item["catch_rate"] for item in self.fish_data)
        random_roll = random.uniform(0, total_catch_rate * 1.2)
        cumulative_rate = 0

        for item in self.fish_data:
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
                    inventory = module_registry.get_module("inventory")
                    inventory.add_item(user_id, item["name"], "case", 1)
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
            SELECT id, name, weight, price
            FROM caught_fish
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "name": row[1], "weight": row[2], "price": row[3]} for row in result]

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
            print("Economy module not found.")
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



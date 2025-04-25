from main import Bot
import random
import sqlite3
import json
import os

class Fishing:
    def __init__(self):
        self.fish_data = self.load_fish_data()
        self.db_path = os.path.join("modules", "data", "fish.db")
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
                fish_name TEXT NOT NULL,
                weight REAL NOT NULL,
                price REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def fish(self, user_id):
        """Simulate fishing and store the result in the database."""
        if not self.fish_data:
            print("No fish data available.")
            return None

        # Randomly select a fish based on catch rate
        total_catch_rate = sum(fish["catch_rate"] for fish in self.fish_data)
        random_roll = random.uniform(0, total_catch_rate)
        cumulative_rate = 0

        for fish in self.fish_data:
            cumulative_rate += fish["catch_rate"]
            if random_roll <= cumulative_rate:
                # Randomize the weight of the fish
                weight = round(random.uniform(fish["min_weight"], fish["max_weight"]), 2)
                # Calculate the price based on the weight and price multiplier
                price = round(weight * fish["price_multiplier"], 2)
                # Add the fish to the database
                self.add_fish_to_db(user_id, fish["fish_name"], weight, price)
                return {"fish_name": fish["fish_name"], "weight": weight, "price": price}

    def add_fish_to_db(self, user_id, fish_name, weight, price):
        """Add a caught fish to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO caught_fish (user_id, fish_name, weight, price)
            VALUES (?, ?, ?, ?)
        """, (user_id, fish_name, weight, price))
        conn.commit()
        conn.close()

    def get_sack(self, user_id):
        """Retrieve all fish caught by the user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fish_name, weight, price
            FROM caught_fish
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "fish_name": row[1], "weight": row[2], "price": row[3]} for row in result]

    def clear_sack(self, user_id):
        """Remove all fish caught by the user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM caught_fish WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def list_fish(self):
        """List all available fish."""
        return self.fish_data

    def eat(self, user_id, fish_name=None):
        """
        Eat the first fish matching the given name from the user's sack, or the first fish if no name is provided.

        :param user_id: The ID of the user.
        :param fish_name: The name of the fish to eat (optional).
        :return: A description of the fish or an error message if the fish is not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if fish_name:
            # Sanitize the fish_name input
            fish_name = fish_name.strip()

            # Retrieve the first fish matching the name (case-insensitive) from the database
            cursor.execute("""
                SELECT id, fish_name
                FROM caught_fish
                WHERE user_id = ? AND LOWER(fish_name) = LOWER(?)
                LIMIT 1
            """, (user_id, fish_name))
        else:
            # Retrieve the first fish in the sack if no name is provided
            cursor.execute("""
                SELECT id, fish_name
                FROM caught_fish
                WHERE user_id = ?
                LIMIT 1
            """, (user_id,))
        
        fish = cursor.fetchone()

        if not fish:
            conn.close()
            return "Your sack is empty." if not fish_name else f"There were no '{fish_name}' found in your sack."

        fish_id, fish_name = fish

        # Remove the fish from the database
        cursor.execute("""
            DELETE FROM caught_fish
            WHERE id = ?
        """, (fish_id,))
        conn.commit()
        conn.close()

        # Retrieve the fish description from the fish data
        for fish_data in self.fish_data:
            if fish_data["fish_name"].lower() == fish_name.lower():
                return fish_data.get("description", "You ate the fish.")

        return "You ate the fish."



import os
import random
import sqlite3
import json
import sys

from util.config import get_config_path
from util.module_registry import module_registry

class Inventory:
    load_after = ["economy"]  # Load after the economy module
    
    def __init__(self):
        appdata_dir = os.path.dirname(get_config_path())
        self.db_path = os.path.join(appdata_dir if hasattr(sys, '_MEIPASS') else "db", "inventory.db")
        try:
            self.initialize_database()
        except Exception as e:
            print(f"Error initializing database: {e}")
            # add info to error
            raise Exception(f"Error initializing database: {e}")
        cases_path = os.path.join(appdata_dir, "cases.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "cases.json")
        try:
            with open(cases_path, mode="r", encoding="utf-8") as file:
                self.cases = json.load(file)
        except Exception as e:
            print(f"Error loading cases: {e}")
            raise Exception(f"Error loading cases: {e}")
        self.economy = module_registry.get_module("economy")

    def initialize_database(self):
        """Initialize the SQLite database for storing user inventories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        print("Initializing database...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_inventory (
                user_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_data TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        cursor.execute("PRAGMA table_info(user_inventory)")
        columns = [column[1] for column in cursor.fetchall()]
        # Check if the item_data column exists, and add it if necessary
        if "item_data" not in columns:
            cursor.execute("ALTER TABLE user_inventory ADD COLUMN item_data TEXT DEFAULT '{}'")
        conn.commit()
        conn.close()

    def add_item(self, user_id, item_name, item_data, quantity=1):
        """Add an item to the user's inventory."""
        item_data = item_data if isinstance(item_data, str) else json.dumps(item_data)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        print(f"Adding item: {item_name} to user: {user_id} with data: {item_data} and quantity: {quantity}")
        cursor.execute("""
            INSERT INTO user_inventory (user_id, item_name, item_data, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?
        """, (user_id, item_name, json.dumps(item_data), quantity, quantity))
        conn.commit()
        conn.close()
        return f"Added {quantity} x {item_name} ({item_data}) to {user_id}'s inventory."

    def remove_item(self, user_id, item_name, quantity=1):
        """Remove an item from the user's inventory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        print(f"Removing item: {item_name} from user: {user_id} with quantity: {quantity}")
        cursor.execute("""
            SELECT quantity FROM user_inventory
            WHERE user_id = ? AND item_name = ? COLLATE NOCASE
        """, (user_id, item_name))
        result = cursor.fetchone()
        if not result or result[0] < quantity:
            conn.close()
            return f"Not enough {item_name} in inventory to remove."
        
        cursor.execute("""
            UPDATE user_inventory
            SET quantity = quantity - ?
            WHERE user_id = ? AND item_name = ?
        """, (quantity, user_id, item_name))
        cursor.execute("""
            DELETE FROM user_inventory
            WHERE user_id = ? AND item_name = ? AND quantity <= 0
        """, (user_id, item_name))
        conn.commit()
        conn.close()
        return f"Removed {quantity} x {item_name} from {user_id}'s inventory."

    def get_item_by_type(self, playername, item_type):
        """Get items of a specific type from the user's inventory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        print(f"Getting items of type: {item_type} for user: {playername}")
        cursor.execute("""
            SELECT item_name, item_data, quantity FROM user_inventory
            WHERE user_id = ?
        """, (playername,))
        items = cursor.fetchall()
        conn.close()
        if not items:
            return None
        found_items = []
        for item in items:
            item_name = item[0]
            item_data = json.loads(item[1])
            quantity = item[2]
            if item_data.get("type").lower() == item_type.lower():
                found_items.append((item_name, item_data, quantity))

        if not found_items:
            return None
        return found_items

    def list_inventory(self, user_id):
        """List all items in the user's inventory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT item_name, item_data, quantity FROM user_inventory
            WHERE user_id = ?
        """, (user_id,))
        items = cursor.fetchall()
        conn.close()
        if not items:
            return None
        return [(item[0], item[1], item[2]) for item in items]

    def open_case(self, user_id, case_name):
        """Open a case and add a random item to the user's inventory."""
        print(f"Opening case: {case_name} for user: {user_id}")
        if case_name:
            user_inv = self.list_inventory(user_id)
            print(f"User inventory: {user_inv}")

            # check if has case
            if not any(case_name in item for item in user_inv):
                return f"You don't have a {case_name} to open."
            
            # check if case is valid
            valid_cases = [case["name"] for case in self.cases]
            if case_name not in valid_cases:
                return f"{case_name} is not a valid case."
            
            # open the case
            # get first case whose ["name"] matches case_name
            case = next((case for case in self.cases if case["name"] == case_name), None)

            # milspec, restricted, classified, covert, and special
            rarities = [.7995, .15, .042, .006, .0025]

            rarity = random.choices(
                ["mil-spec", "restricted", "classified", "covert", "exceedingly-rare"],
                weights=rarities,
                k=1
            )[0]

            item = random.choice(case["items"][rarity])

            # remove case from inventory
            self.remove_item(user_id, case_name, 1)
            
            self.economy.add_balance(user_id, item['price'])
            return f"You opened a {case_name} and got a {item['name']} worth {item['price']}! You sell it and pocket the change."

        else:
            # open the first case in the inventory
            user_inv = self.list_inventory(user_id)
            if not user_inv:
                return f"Rummaging through your inventory, you find nothing but dust."
            
            # find first item that has "Case" in it
            case_name = next((item[0] for item in user_inv if "Case" in item[0]), None)

            if not case_name:
                return None
            return self.open_case(user_id, case_name)

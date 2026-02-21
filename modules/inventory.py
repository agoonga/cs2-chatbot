import os
import random
import json
import sys
from thefuzz import process, fuzz

from util.database import DatabaseConnection
from util.config import get_config_path
from util.module_registry import module_registry
from modules.economy import Economy

class Inventory:
    load_after = ["economy"]  # Load after the economy module
    
    def __init__(self):
        appdata_dir = os.path.dirname(get_config_path())
        cases_path = os.path.join(appdata_dir, "cases.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "cases.json")
        items_path = os.path.join(appdata_dir, "fish.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "fish.json")
        shop_path = os.path.join(appdata_dir, "shop.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "shop.json")
        try:
            with open(cases_path, mode="r", encoding="utf-8") as file:
                case_data = json.load(file)
                self.case = {}
                for item in case_data:
                    self.case[item["name"]] = item
        except Exception as e:
            raise Exception(f"Error loading cases: {e}")
        try:
            with open(items_path, mode="r", encoding="utf-8") as file:
                items_data = json.load(file)
                self.items = {}
                for item in items_data:
                    self.items[item["name"]] = item
        except Exception as e:
            raise Exception(f"Error loading items: {e}")
        try:
            with open(shop_path, mode="r", encoding="utf-8") as file:
                shop_data = json.load(file)
                self.shop = {}
                for category in shop_data.values():
                    for item in category:
                        self.shop[item["name"]] = item
        except Exception as e:
            raise Exception(f"Error loading shop data: {e}")
        
        self.economy: Economy = module_registry.get_module("economy")

    def add_item(self, user_id, item_name, quantity=1):
        """Add an item to the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO user_inventory (user_id, item_name, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = user_inventory.quantity + %s
            """, (user_id, item_name, quantity, quantity))
        return f"Added {quantity} x {item_name} to {user_id}'s inventory."

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
                SELECT item_name, quantity FROM user_inventory
                WHERE user_id = %s
            """, (playername,))
            items = cursor.fetchall()
        if not items:
            return None
        found_items = []
        for item in items:
            item_name = item[0]
            item_data = self.shop.get(item_name) or (self.items).get(item_name)
            quantity = item[1]
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
                SELECT item_name, quantity FROM user_inventory
                WHERE user_id = %s
            """, (user_id,))
            items = cursor.fetchall()
        if not items:
            return None
        return [{'name': item[0],'quantity': item[1]} for item in items]

    def open_case(self, user_id, case_name):
        """Open a case and add a random item to the user's inventory."""
        if case_name:
            user_inv = self.list_inventory(user_id)

            # check if has case
            if not any(case_name.lower() in item['name'].lower() for item in user_inv):
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
            case_name = next((item['name'] for item in user_inv if "Case" in item['name']), None)

            if not case_name:
                return None
            return self.open_case(user_id, case_name)

    def get_item_by_name(self, user_id, item_name):
        """Get an item by its name from the user's inventory."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT item_name, quantity FROM user_inventory
                WHERE user_id = %s AND item_name ILIKE %s
            """, (user_id, item_name))
            result = cursor.fetchone()
        if not result:
            return None
        return {
            "name": result[0],
            "data": self.shop.get(result[0]) or self.items.get(result[0]),
            "quantity": result[1]
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

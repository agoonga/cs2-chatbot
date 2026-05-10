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
        try:
            with open(cases_path, mode="r", encoding="utf-8") as file:
                self.cases = json.load(file)
        except Exception as e:
            raise Exception(f"Error loading cases: {e}")
        self.economy: Economy = module_registry.get_module("economy")

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
        if case_name:
            user_inv = self.list_inventory(user_id)

            # check if has case
            if not any(case_name.lower() in item['name'].lower() for item in user_inv):
                return self._translate(
                    t,
                    "commands.inventory.open.no_case_named",
                    "You don't have a {case_name} to open.",
                    case_name=case_name,
                )
            
            # check if case is valid
            valid_cases = [case["name"] for case in self.cases]
            if case_name not in valid_cases:
                return self._translate(
                    t,
                    "commands.inventory.open.invalid_case",
                    "{case_name} is not a valid case.",
                    case_name=case_name,
                )
            
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
            return self._translate(
                t,
                "commands.inventory.open.opened_case",
                "You opened a {case_name} and got a {item_name} worth {price}! You sell it and pocket the change.",
                case_name=case_name,
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
            
            # find first item that has "Case" in it
            case_name = next((item['name'] for item in user_inv if "Case" in item['name']), None)

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

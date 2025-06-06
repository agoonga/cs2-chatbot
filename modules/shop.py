import os
import json
import sys
from thefuzz import process, fuzz

from util.config import get_config_path
from util.module_registry import module_registry
from modules.economy import Economy
from modules.inventory import Inventory

class Shop:
    load_after = ["economy", "inventory"]  # Load after the economy and inventory modules
    
    def __init__(self):
        appdata_dir = os.path.dirname(get_config_path())
        shop_path = os.path.join(appdata_dir, "shop.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "shop.json")
        try:
            with open(shop_path, mode="r", encoding="utf-8") as file:
                self.shop = json.load(file)
        except Exception as e:
            raise Exception(f"Error loading shop: {e}")
        self.economy: Economy = module_registry.get_module("economy")
        self.inventory: Inventory = module_registry.get_module("inventory")

        self.load_shop_categories()

    def find_category(self, item_name, categories):
        """Find the category of an item by its name."""
        for category, items in categories.items():
            for item in items:
                if item["name"].lower() == item_name.lower() or item_name.lower() in [alias.lower() for alias in item.get("aliases", [])]:
                    return category
                best_match, score = process.extractOne(item_name.lower(), [i["name"].lower() for i in items], scorer=fuzz.ratio)
                if best_match and score >= 80:
                    return category

        return None

    def find_item(self, item_name, allowed_items):
        """
        Find an item in the allowed shop items by its name or aliases.

        :param item_name: The name of the item to find.
        :param allowed_items: The list of allowed shop items.
        :return: The item if found, otherwise None.
        """
        for item in allowed_items["items"]:
            if item["name"].lower() == item_name or item_name in [alias.lower() for alias in item.get("aliases", [])]:
                return item
        
        best_match, score = process.extractOne(item_name, [item["name"].lower() for item in allowed_items["items"]], scorer=fuzz.ratio)
        if best_match and score >= 60:
            for item in allowed_items["items"]:
                if item["name"].lower() == best_match:
                    return item

        return None

    def buy(self, playername, item_name, quantity=1):
        """
        Buy an item from the shop.

        :param playername: The name of the player.
        :param item_name: The name of the item to buy.
        :param quantity: The quantity of the item to buy.
        :return: A dictionary with success or error information.
        """
        # Ensure quantity is an integer
        try:
            quantity = int(quantity)
        except ValueError:
            return {"error": "Invalid quantity."}

        item_name = item_name.lower()

        # Check if the item is in the player's shop
        category = self.find_category(item_name, self.categories)
        if category is None:
            return {"error": "The shopkeeper sighs and says: 'I don't have that item.'"}

        allowed_items = self.get_shop_items(playername, category)
        if type(allowed_items) == dict and "error" in allowed_items.keys():
            return allowed_items

        # Find the item using the new find_item method
        trying_to_buy = self.find_item(item_name, allowed_items)
        if trying_to_buy is None:
            return {"error": "The shopkeeper sighs and says: 'I don't have that item.'"}

        # Check if quantity is valid
        if quantity < 1:
            return {"error": "Invalid quantity."}
        if quantity > 1:
            # Check if the item is a stackable item
            if trying_to_buy.get("max") is not None and quantity > trying_to_buy["max"]:
                return {"error": f"You can only have {trying_to_buy['max']} of this item at a time."}

        # Check if the player has enough money
        player_money = self.economy.get_balance(playername)
        if player_money < trying_to_buy["price"] * quantity:
            return {"error": "The shopkeeper says: 'Isn't that too rich for your blood?'"}

        # Add the item to the player's inventory
        try:
            self.economy.deduct_balance(playername, trying_to_buy["price"] * quantity)
            money_left = self.economy.get_balance(playername)
            self.inventory.add_item(playername, trying_to_buy["name"], trying_to_buy, quantity)
            if trying_to_buy.get("replaces") is not None:
                # Remove the replaced item from the inventory
                if isinstance(trying_to_buy["replaces"], str):
                    trying_to_buy["replaces"] = [trying_to_buy["replaces"]]
                for replace in trying_to_buy["replaces"]:
                    self.inventory.remove_item(playername, replace, quantity)
            return {"success": f"You bought {f'{quantity} x' if quantity > 1 else 'a'} '{trying_to_buy['name']}'. Your new balance is ${money_left}."}
        except Exception as e:
            return {"error": f"Error while processing the purchase: {e}"}
                
        

    def load_shop_categories(self):
        """Load shop categories and items from the JSON file."""
        self.categories = {}
        for category, items in self.shop.items():
            self.categories[category] = items

    def get_categories(self):
        """Get the available categories in the shop."""
        return self.categories.keys()

    def get_shop_items(self, playername, category=None):
        """Get the items in the shop, optionally filtered by category."""
        category = category.lower() if category else None
        chosen_category = None
        for cat in self.categories.keys():
            if cat.lower() == category:
                chosen_category = cat
                break
        if not chosen_category:
            return {"error": "Category not found. Available categories: " + ", ".join(self.categories.keys())}
        
        items = self.categories[chosen_category]
        if not items:
            return {"error": "No items available in this category."}

        items = self._add_allowed_count_to_shop(playername, items)
        return {"items": items}

    def _add_allowed_count_to_shop(self, playername, items):
        """Add the allowed count to each item in the shop."""
        inventory = self.inventory.list_inventory(playername)
        if not inventory:
            inventory = []
        
        # get the item names from the inventory
        user_has = [item['name'] for item in inventory]

        allowed_shop_items = []
        stop_at_items = []
        # see if any of the items replace anything (item["replaces"])
        if any(item.get("replaces") is not None for item in items):
            for item in reversed(items):
                if item.get("name") in user_has:
                    break
                if item.get("name") in stop_at_items:
                    break
                if item.get("replaces") is not None:
                    # check if the item is in the inventory
                    if type(item["replaces"]) == str:
                        if item["replaces"] in user_has:
                            allowed_shop_items.append(item)
                            stop_at_items.append(item["replaces"])
                            continue
                    else:
                        # check if any of the items in the replaces list are in the inventory
                        for replace in item["replaces"]:
                            if replace in user_has:
                                allowed_shop_items.append(item)
                                stop_at_items.append(replace)
                                break
                else:
                    # if the item is not in the inventory, add it to the allowed shop items
                    allowed_shop_items.append(item)
        else:
            # if no items replace anything, check for max count (item["max"])
            for item in items:
                if item not in user_has:
                    allowed_shop_items.append(item)
                    continue
                if item.get("max") is not None:
                    # get the allowed buy count (count_has - max)
                    # inventory is an array of tuples (item_name, item_type, quantity)
                    for i in inventory:
                        if i[0] == item["name"]:
                            count_has = i[2]
                            break
                    if count_has < item["max"]:
                        allowed_shop_items.append(item)
                        continue
                    else:
                        continue
                else:
                    allowed_shop_items.append(item)

        if not allowed_shop_items:
            return {"error": "The shopkeeper says: 'I don't have anything for you.'"}
        return allowed_shop_items
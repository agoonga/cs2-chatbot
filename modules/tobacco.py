import json
import os
import sys
from thefuzz import process, fuzz

from util.config import get_config_path
from util.module_registry import module_registry
from modules.inventory import Inventory
from modules.status_effects import StatusEffects

class Tobacco:
    load_after = ["inventory"]
    def __init__(self):
        self.tobacco_data = self.load_tobacco_data()
        self.inventory: Inventory = module_registry.get_module("inventory")
        self.status_effects: StatusEffects = module_registry.get_module("status_effects")
    
    def load_tobacco_data(self):
        """
        Load tobacco data from the configuration file.
        """
        appdata_dir = os.path.dirname(get_config_path())
        tobacco_json_path = os.path.join(appdata_dir, "tobacco.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "tobacco.json")
        try:
            with open(tobacco_json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def find_tobacco(self, tobacco_name):
        """
        Find a tobacco by its name.
        """
        if self.tobacco_data is None:
            return None
        
        # fuzz the tobacco name
        tobacco_names = [tobacco["name"].lower() for tobacco in self.tobacco_data]
        best_match = process.extractOne(tobacco_name.lower(), tobacco_names, scorer=fuzz.ratio)
        if best_match and best_match[1] >= 80:
            for tobacco in self.tobacco_data:
                if tobacco["name"].lower() == best_match[0]:
                    return tobacco
        
        return None

    def smoke_tobacco(self, playername, tobacco):
        """
        Simulate smoking tobacco
        """
        tobacco_data = self.find_tobacco(tobacco)
        if tobacco_data is None:
            return f"Tobacco '{tobacco}' not found."
        
        # Check if the player has the tobacco in their inventory
        if not self.inventory.get_item_by_name(playername, tobacco_data["name"]):
            return f"You don't have any {tobacco_data['name']} to chuff."
        
        # Remove the tobacco from the inventory
        self.inventory.remove_item(playername, tobacco_data["name"], 1)
        
        # Apply the effects of drinking the tobacco
        effect_descs = []
        for effect in tobacco_data.get("effects", []):
            self.status_effects.add_effect(playername, effect)
            effect_descs.append(self.status_effects.get_description(effect))
        
        return f"You chuff a {tobacco_data['name']}. ({', '.join(effect_descs)})"


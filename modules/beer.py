import json
import os
import sys
from thefuzz import process, fuzz

from util.config import get_config_path
from util.module_registry import module_registry
from modules.inventory import Inventory
from modules.status_effects import StatusEffects

class Beer:
    load_after = ["inventory"]
    def __init__(self):
        self.beer_data = self.load_beer_data()
        self.inventory: Inventory = module_registry.get_module("inventory")
        self.status_effects: StatusEffects = module_registry.get_module("status_effects")
    
    def load_beer_data(self):
        """
        Load drinking data from the configuration file.
        """
        appdata_dir = os.path.dirname(get_config_path())
        beer_json_path = os.path.join(appdata_dir, "beer.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "beer.json")
        try:
            with open(beer_json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def find_beer(self, beer_name):
        """
        Find a beer by its name.
        """
        if self.beer_data is None:
            return None
        
        # fuzz the beer name
        beer_names = [beer["name"].lower() for beer in self.beer_data]
        best_match = process.extractOne(beer_name.lower(), beer_names, scorer=fuzz.ratio)
        if best_match and best_match[1] >= 80:
            for beer in self.beer_data:
                if beer["name"].lower() == best_match[0]:
                    return beer
        
        return None

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def drink_beer(self, playername, beer, t=None):
        """
        Simulate drinking a beer.
        """
        beer_data = self.find_beer(beer)
        if beer_data is None:
            return self._translate(t, "commands.drink.beer_not_found", "Beer '{beer}' not found.", beer=beer)
        
        # Check if the player has the beer in their inventory
        if not self.inventory.get_item_by_name_fuzzy(playername, beer_data["name"]):
            return self._translate(
                t,
                "commands.drink.no_beer_named",
                "You don't have any {beer_name} to drink.",
                beer_name=beer_data["name"],
            )
        
        # Remove the beer from the inventory
        self.inventory.remove_item(playername, beer_data["name"], 1)
        
        # Apply the effects of drinking the beer
        effect_descs = []
        for effect in beer_data.get("effects", []):
            normalized_effect = effect.strip().lower()
            result = self.status_effects.add_effect(playername, normalized_effect)
            description = self.status_effects.get_description(normalized_effect)
            if result is not True and description is None:
                effect_descs.append(str(result))
            elif description:
                effect_descs.append(description)
        
        return self._translate(
            t,
            "commands.drink.drank",
            "You drink a {beer_name}. ({effects})",
            beer_name=beer_data["name"],
            effects=', '.join(effect_descs),
        )


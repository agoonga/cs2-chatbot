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

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def smoke_tobacco(self, playername, tobacco, t=None):
        """
        Simulate smoking tobacco
        """
        tobacco_data = self.find_tobacco(tobacco)
        if tobacco_data is None:
            return self._translate(t, "commands.smoke.tobacco_not_found", "Tobacco '{tobacco}' not found.", tobacco=tobacco)
        
        # Check if the player has the tobacco in their inventory
        if not self.inventory.get_item_by_name_fuzzy(playername, tobacco_data["name"]):
            return self._translate(
                t,
                "commands.smoke.no_tobacco_named",
                "You don't have any {tobacco_name} to chuff.",
                tobacco_name=tobacco_data["name"],
            )
        
        # Remove the tobacco from the inventory
        self.inventory.remove_item(playername, tobacco_data["name"], 1)
        
        # Apply the effects of drinking the tobacco
        effect_descs = []
        for effect in tobacco_data.get("effects", []):
            normalized_effect = effect.strip().lower()
            result = self.status_effects.add_effect(playername, normalized_effect)
            description = self.status_effects.get_description(normalized_effect)
            if result is not True and description is None:
                effect_descs.append(str(result))
            elif description:
                effect_descs.append(description)
        
        return self._translate(
            t,
            "commands.smoke.smoked",
            "You chuff a {tobacco_name}. ({effects})",
            tobacco_name=tobacco_data["name"],
            effects=', '.join(effect_descs),
        )


import json
import os
import sys
from time import time

from util.database import DatabaseConnection
from util.config import get_config_path
from util.module_registry import module_registry

class StatusEffects:
    def __init__(self):
        self.status_effect_data: dict = self.load_status_effects()

    def load_status_effects(self):
        """Load status effects data from the configuration file."""
        appdata_dir = os.path.dirname(get_config_path())
        effects_json_path = os.path.join(appdata_dir, "status_effects.json") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "status_effects.json")
        try:
            with open(effects_json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def find_effect(self, module_id, effect_id):
        """Find an effect data by its name."""
        if self.status_effect_data is None:
            return None
        
        if module_id.lower() in self.status_effect_data.keys():
            module_to_search = self.status_effect_data[module_id.lower()]
            if effect_id.lower() in module_to_search.keys():
                found_effect = module_to_search[effect_id.lower()]
                found_effect["module_id"] = module_id.lower()
                found_effect["effect_id"] = effect_id.lower()
                return found_effect
        
        return None

    def add_effect(self, playername, effect_name):
        """Add a status effect to the user."""
        module_id, effect_id = effect_name.split(".", 1)
        effect_data = self.find_effect(module_id, effect_id)
        if effect_data is None:
            return f"Effect '{effect_name}' not found."
        
        # check if the effect already exists
        active_effects = self.get_effects(playername)
        print(active_effects)
        existing_effect = next((e for e in active_effects if e["effect_id"] == effect_id), None)
        print(existing_effect)
        
        with DatabaseConnection() as cursor:
            if existing_effect:
                duration = existing_effect["duration"]
                # add the duration to the existing effect
                new_expires_at = int(time()) + duration + effect_data["duration"]
                cursor.execute("""
                    UPDATE status_effects
                    SET expiration_time = %s
                    WHERE user_id = %s AND effect_name = %s
                """, (new_expires_at, playername, effect_name))
            else:
                # add a new effect
                expires_at = int(time()) + effect_data["duration"]
                cursor.execute("""
                    INSERT INTO status_effects (user_id, effect_name, expiration_time)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, effect_name) DO UPDATE SET expiration_time = EXCLUDED.expiration_time
                """, (playername, effect_name, expires_at))

        return True
    
    def get_effects(self, playername):
        """Get all active status effects for a user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT effect_name, expiration_time FROM status_effects
                WHERE user_id = %s
            """, (playername,))
            effects = cursor.fetchall()

        active_effect_names = []
        for effect_id, expires_at in effects:
            if expires_at > int(time()):
                active_effect_names.append((effect_id, expires_at))
            else:
                # Remove expired effect
                self.remove_effect(playername, effect_id)

        active_effects = []
        for (effect_name, expires_at) in active_effect_names:
            effect = self.find_effect(*effect_name.split(".", 1))
            effect["duration"] = expires_at - int(time())
            active_effects.append(effect)

        return active_effects

    
    def remove_effect(self, playername, effect_id):
        """Remove a status effect from the user."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                DELETE FROM status_effects
                WHERE user_id = %s AND effect_name = %s
            """, (playername, effect_id))

        return True

    def get_description(self, effect_name):
        """Get the description of a status effect."""
        module_id, effect_id = effect_name.split(".", 1)
        effect_data = self.find_effect(module_id, effect_id)
        if effect_data is None:
            return None
        
        return effect_data.get("description", "You feel bubbly")
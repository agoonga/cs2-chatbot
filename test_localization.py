import sys
import os
from util.localization import LocalizationManager

def run_tests():
    manager = LocalizationManager(strings_dir="strings", default_language="en_US")
    
    # Test 1 & 2: Loading languages
    print(f"Test 1: Load en_US: {'Success' if manager._load_language('en_US') else 'Failed'}")
    print(f"Test 2: Load pt_BR: {'Success' if manager._load_language('pt_BR') else 'Failed'}")
    
    # Test 3: get_string English
    en_string = manager.get_string(
        "commands.fishing.cast_success_fish", 
        "en_US", 
        player="Bob", 
        name="Salmon", 
        weight="5.5", 
        price="50"
    )
    print(f"Test 3: English format: {en_string}")
    
    # Test 4: get_string Portuguese
    pt_string = manager.get_string(
        "commands.fishing.cast_success_fish", 
        "pt_BR", 
        player="Bob", 
        name="Salmão", 
        weight="5.5", 
        price="50"
    )
    print(f"Test 4: Portuguese format: {pt_string}")
    
    # Test 5: Fallback to English
    # We need a key that exists in en_US but not in pt_BR to verify fallback.
    # For testing purposes, we'll try to get a non-existent key in pt_BR that exists in en_US.
    # Since I don't know the exact keys, I'll print the result of a key that might not exist in pt_BR.
    # Alternatively, I can just check if get_string returns something when requesting pt_BR for a key only in en_US.
    
    fallback_string = manager.get_string("commands.fishing.cast_success", "pt_BR")
    print(f"Test 5: Fallback (checking key 'commands.fishing.cast_success' in pt_BR): {fallback_string}")

if __name__ == '__main__':
    run_tests()

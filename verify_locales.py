import os
import json
import re

locales_dir = "strings"
source_locale = "en_US"
exclude_locales = ["en_US", "en_SG"]
keys_to_verify = [
    "commands.autosell.add_all_success",
    "commands.trophy.unknown_subcommand",
    "errors.spam_cooldown"
]

def get_nested_value(data, key_path):
    keys = key_path.split('.')
    for k in keys:
        if not isinstance(data, dict): return None
        data = data.get(k, {})
    return data if isinstance(data, str) else None

def extract_placeholders(text):
    return set(re.findall(r'\{[^}]+\}', text))

with open(os.path.join(locales_dir, f"{source_locale}.json"), "r", encoding="utf-8") as f:
    source_data = json.load(f)

source_placeholders = {key: extract_placeholders(get_nested_value(source_data, key) or "") for key in keys_to_verify}

all_passed = True
for filename in os.listdir(locales_dir):
    if not filename.endswith(".json"): continue
    locale = filename[:-5]
    if locale in exclude_locales: continue
    
    with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
        target_data = json.load(f)
    
    for key in keys_to_verify:
        target_val = get_nested_value(target_data, key)
        if target_val is None:
            # print(f"[{locale}] Key {key} MISSING")
            all_passed = False
            continue
        
        target_placeholders = extract_placeholders(target_val)
        expected = source_placeholders[key]
        
        if not expected.issubset(target_placeholders):
            print(f"[{locale}] Key {key} placeholder mismatch: Expected {expected}, got {target_placeholders}")
            all_passed = False

if all_passed:
    print("Placeholder verification: PASSED")
else:
    print("Placeholder verification: FAILED")

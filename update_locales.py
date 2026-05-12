import os
import json
import re
from deep_translator import GoogleTranslator

# Configuration
locales_dir = "strings"
source_locale = "en_US"
exclude_locales = ["en_US", "en_SG"]
keys_to_update = [
    "commands.autosell.add_all_success",
    "commands.trophy.unknown_subcommand",
    "errors.spam_cooldown"
]
mapping = {
    "de_DE": "de", "es_ES": "es", "fr_FR": "fr", "it_IT": "it",
    "ja_JP": "ja", "ko_KR": "ko", "nl_NL": "nl", "pl_PL": "pl",
    "pt_BR": "pt", "ru_RU": "ru", "sv_SE": "sv", "tr_TR": "tr",
    "zh_CN": "zh-CN", "hi_IN": "hi", "el_GR": "el"
}

def get_nested_value(data, key_path):
    keys = key_path.split('.')
    for k in keys:
        if not isinstance(data, dict): return None
        data = data.get(k, {})
    return data if isinstance(data, str) else None

def set_nested_value(data, key_path, value):
    keys = key_path.split('.')
    for k in keys[:-1]:
        data = data.setdefault(k, {})
    data[keys[-1]] = value

# Load source strings
with open(os.path.join(locales_dir, f"{source_locale}.json"), "r", encoding="utf-8") as f:
    source_data = json.load(f)

# Update locales
for filename in os.listdir(locales_dir):
    if not filename.endswith(".json"): continue
    locale = filename[:-5]
    if locale in exclude_locales: continue
    
    file_path = os.path.join(locales_dir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        target_data = json.load(f)
    
    target_lang = mapping.get(locale)
    if not target_lang: continue
    
    changed_count = 0
    translator = GoogleTranslator(source="en", target=target_lang)
    
    for key in keys_to_update:
        src_val = get_nested_value(source_data, key)
        if not src_val: continue
        
        placeholders = re.findall(r'\{[^}]+\}', src_val)
        temp_val = src_val
        for i, p in enumerate(placeholders):
            temp_val = temp_val.replace(p, f"[[{i}]]")
            
        try:
            translated = translator.translate(temp_val)
            for i, p in enumerate(placeholders):
                translated = re.sub(rf'\[\[\s*{i}\s*\]\]', p, translated)
            
            set_nested_value(target_data, key, translated)
            changed_count += 1
        except Exception as e:
            print(f"Error translating {key} for {locale}: {e}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(target_data, f, indent=4, ensure_ascii=False)
    print(f"{locale}: {changed_count} keys updated")

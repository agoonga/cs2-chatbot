import json
import glob
import os
from deep_translator import GoogleTranslator

# Config
SOURCE_LOCALE = "en_US"
EXCLUDE_LOCALES = ["en_US", "en_SG"]
KEYS_TO_TRANSLATE = [
    "commands.autosell.add_all_success",
    "commands.trophy.unknown_subcommand",
    "errors.spam_cooldown"
]

# Map locale to deep_translator codes
LOCALE_MAP = {
    "zh_CN": "zh-CN",
    "zh_TW": "zh-TW",
    "pt_BR": "pt",
    "es_ES": "es"
}

def get_nested(data, key):
    parts = key.split('.')
    for p in parts:
        data = data[p]
    return data

def set_nested(data, key, val):
    parts = key.split('.')
    for p in parts[:-1]:
        data = data[p]
    data[parts[-1]] = val

def main():
    with open(f"strings/{SOURCE_LOCALE}.json", "r", encoding="utf-8") as f:
        source_data = json.load(f)

    total_changes = 0
    all_json_files = glob.glob("strings/*.json")
    
    for path in all_json_files:
        locale = os.path.basename(path).replace(".json", "")
        if locale in EXCLUDE_LOCALES:
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            target_data = json.load(f)
            
        locale_changes = 0
        target_lang = LOCALE_MAP.get(locale, locale.split("_")[0])
        
        try:
            translator = GoogleTranslator(source="en", target=target_lang)
        except Exception as e:
            print(f"Skipping {locale}: {e}")
            continue
        
        for key in KEYS_TO_TRANSLATE:
            source_val = get_nested(source_data, key)
            target_val = get_nested(target_data, key)
            
            if target_val == source_val:
                try:
                    translated = translator.translate(source_val)
                    set_nested(target_data, key, translated)
                    locale_changes += 1
                except Exception as e:
                    print(f"Error translating {key} for {locale}: {e}")
        
        if locale_changes > 0:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(target_data, f, indent=4, ensure_ascii=False)
            print(f"{locale}: {locale_changes} keys changed")
            total_changes += locale_changes

    print(f"Total keys changed: {total_changes}")

if __name__ == '__main__':
    main()

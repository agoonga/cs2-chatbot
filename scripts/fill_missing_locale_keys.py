import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS_DIR = ROOT / "strings"
BASE = "en_US"


def deep_merge_missing(target, source):
    if not isinstance(target, dict) or not isinstance(source, dict):
        return

    for key, value in source.items():
        if key not in target:
            target[key] = value
            continue

        if isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge_missing(target[key], value)


def main():
    base_path = STRINGS_DIR / f"{BASE}.json"
    with base_path.open("r", encoding="utf-8") as handle:
        base_data = json.load(handle)

    updated = []
    for locale_path in sorted(STRINGS_DIR.glob("*.json")):
        if locale_path.stem == BASE:
            continue

        with locale_path.open("r", encoding="utf-8") as handle:
            locale_data = json.load(handle)

        before = json.dumps(locale_data, ensure_ascii=False, sort_keys=True)
        deep_merge_missing(locale_data, base_data)
        after = json.dumps(locale_data, ensure_ascii=False, sort_keys=True)

        if before != after:
            locale_path.write_text(
                json.dumps(locale_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            updated.append(locale_path.name)

    print("Updated locales:", ", ".join(updated) if updated else "none")


if __name__ == "__main__":
    main()

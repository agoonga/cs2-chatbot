import json
from pathlib import Path
import string

from util.localization import LocalizationManager


STRINGS_DIR = Path(__file__).resolve().parents[1] / "strings"


class PlaceholderValue:
    """Format-compatible placeholder value for any format spec."""

    def __format__(self, _spec):
        return "X"

    def __str__(self):
        return "X"


def flatten_dict(data, parent_key=""):
    items = {}
    if not isinstance(data, dict):
        return items

    for key, value in data.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key))
        else:
            items[new_key] = value
    return items


def extract_placeholders(template):
    fields = set()
    for _literal, field_name, _format_spec, _conversion in string.Formatter().parse(template):
        if field_name:
            # Normalize field names like "player!r" or nested style segments.
            fields.add(field_name.split("!")[0].split(":")[0])
    return fields


def build_replacement_args(placeholders):
    return {name: PlaceholderValue() for name in placeholders}


def load_flattened_locale(locale_code):
    path = STRINGS_DIR / f"{locale_code}.json"
    with path.open("r", encoding="utf-8") as handle:
        return flatten_dict(json.load(handle))


def test_text_replacement_for_all_locale_strings():
    manager = LocalizationManager(strings_dir=str(STRINGS_DIR), default_language="en_US")

    locale_files = sorted(p.stem for p in STRINGS_DIR.glob("*.json"))

    for locale in locale_files:
        flattened = load_flattened_locale(locale)
        for key, value in flattened.items():
            if not isinstance(value, str):
                continue

            placeholders = extract_placeholders(value)
            args = build_replacement_args(placeholders)
            rendered = manager.get_string(key, language=locale, **args)

            assert isinstance(rendered, str), f"{locale}:{key} did not return a string"

            # If no placeholders exist, output should match source value exactly.
            if not placeholders:
                assert rendered == value, f"{locale}:{key} changed unexpectedly"
                continue

            # For placeholders, ensure replacement happened and placeholders are not leaked.
            for field in placeholders:
                assert "{" + field in value
                assert "{" + field not in rendered, f"{locale}:{key} left placeholder '{field}' unreplaced"


def test_text_replacement_fallback_behavior_for_missing_locale_key():
    manager = LocalizationManager(strings_dir=str(STRINGS_DIR), default_language="en_US")

    # Key is now translated in es_ES (previously was fallback to en_US).
    rendered = manager.get_string("commands.scramble.start", language="es_ES", word=PlaceholderValue())

    assert "La primera persona que descifre la palabra gana:" in rendered
    assert "{" not in rendered

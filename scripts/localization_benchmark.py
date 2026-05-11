import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS_DIR = ROOT / "strings"
REPORT_PATH = ROOT / "localization_benchmark_report.json"
BASE_LOCALE = "en_US"


def flatten(data, prefix=""):
    items = {}
    if not isinstance(data, dict):
        return items

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            items.update(flatten(value, full_key))
        else:
            items[full_key] = value
    return items


def placeholder_set(text):
    if not isinstance(text, str):
        return set()
    return set(re.findall(r"\{([^{}]+)\}", text))


def load_locale(locale_code):
    locale_path = STRINGS_DIR / f"{locale_code}.json"
    with locale_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_code_localization_keys():
    # Captures direct string key usage in common localization call patterns.
    patterns = [
        re.compile(r"\b(?:bot\.t|self\.t|server\.t)\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\b(?:get_string|get_value)\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"\b_translate\(\s*[^,]+,\s*['\"]([^'\"]+)['\"]"),
    ]

    excluded_dirs = {".git", ".venv", "__pycache__", "node_modules"}
    keys = set()

    for py_file in ROOT.rglob("*.py"):
        if any(part in excluded_dirs for part in py_file.parts):
            continue

        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                key = match.group(1)
                # Ignore obvious non-key strings.
                if "." in key and " " not in key:
                    keys.add(key)

    return sorted(keys)


def build_report():
    base_data = flatten(load_locale(BASE_LOCALE))
    base_keys = set(base_data.keys())

    code_keys = set(find_code_localization_keys())
    en_missing = sorted(k for k in code_keys if k not in base_keys)

    locale_report = {}
    for locale_file in sorted(STRINGS_DIR.glob("*.json")):
        locale = locale_file.stem
        if locale == BASE_LOCALE:
            continue

        locale_data = flatten(load_locale(locale))
        locale_keys = set(locale_data.keys())

        missing = sorted(base_keys - locale_keys)
        extra = sorted(locale_keys - base_keys)

        mismatches = []
        for key in sorted(base_keys & locale_keys):
            base_val = base_data[key]
            locale_val = locale_data[key]
            if isinstance(base_val, str) and isinstance(locale_val, str):
                p_base = placeholder_set(base_val)
                p_locale = placeholder_set(locale_val)
                if p_base != p_locale:
                    mismatches.append(
                        {
                            "key": key,
                            "base_placeholders": sorted(p_base),
                            "locale_placeholders": sorted(p_locale),
                        }
                    )

        locale_report[locale] = {
            "missing_keys": missing,
            "extra_keys": extra,
            "placeholder_mismatches": mismatches,
        }

    report = {
        "base_locale": BASE_LOCALE,
        "en_us_missing_code_keys": en_missing,
        "locales": locale_report,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def print_summary(report):
    print(f"Base locale: {report['base_locale']}")
    print(f"English missing code keys: {len(report['en_us_missing_code_keys'])}")
    if report["en_us_missing_code_keys"]:
        print("  Example:", report["en_us_missing_code_keys"][0])

    for locale, data in report["locales"].items():
        print(
            f"{locale}: missing={len(data['missing_keys'])}, "
            f"extra={len(data['extra_keys'])}, "
            f"mismatches={len(data['placeholder_mismatches'])}"
        )

    print(f"Report written to: {REPORT_PATH}")


if __name__ == "__main__":
    report_data = build_report()
    print_summary(report_data)

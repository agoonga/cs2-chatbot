import json
import re
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
STRINGS_DIR = ROOT / "strings"
REPORT_PATH = ROOT / "untranslated_fallback_report.json"
BASE_LOCALE = "en_US"

LANG_MAP = {
    "de_DE": "de",
    "es_ES": "es",
    "fr_FR": "fr",
    "it_IT": "it",
    "ja_JP": "ja",
    "ko_KR": "ko",
    "nl_NL": "nl",
    "pl_PL": "pl",
    "pt_BR": "pt",
    "ru_RU": "ru",
    "sv_SE": "sv",
    "tr_TR": "tr",
    "zh_CN": "zh-CN",
    "en_SG": "en",
    "hi_IN": "hi",
    "he_IL": "iw",
    "fi_FI": "fi",
    "el_GR": "el",
}

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
TOKEN_RE = re.compile(r"__PH(\d+)__")


def get_nested(data, dotted_key):
    current = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_nested(data, dotted_key, value):
    parts = dotted_key.split(".")
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def protect_placeholders(text):
    placeholders = []

    def repl(match):
        placeholders.append(match.group(0))
        return f"__PH{len(placeholders) - 1}__"

    protected = PLACEHOLDER_RE.sub(repl, text)
    return protected, placeholders


def restore_placeholders(text, placeholders):
    def repl(match):
        idx = int(match.group(1))
        if 0 <= idx < len(placeholders):
            return placeholders[idx]
        return match.group(0)

    return TOKEN_RE.sub(repl, text)


def translate_text(translator, text):
    protected, placeholders = protect_placeholders(text)
    translated = translator.translate(protected)
    translated = restore_placeholders(translated, placeholders)
    return translated


def main():
    if not REPORT_PATH.exists():
        raise FileNotFoundError("Run untranslated fallback report generation first.")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    
    english_variants = {"en_SG"}  # Skip English regional variants

    changed_locales = {}

    # Report format is a top-level locale -> [keys] map.
    locale_key_map = report.get("identical_values") if isinstance(report.get("identical_values"), dict) else report

    for locale, keys in locale_key_map.items():
        if locale == BASE_LOCALE or not keys:
            continue
        
        if locale in english_variants:
            continue  # Skip English variants

        target_lang = LANG_MAP.get(locale)
        if not target_lang:
            continue

        locale_path = STRINGS_DIR / f"{locale}.json"
        if not locale_path.exists():
            continue

        data = json.loads(locale_path.read_text(encoding="utf-8"))
        translator = GoogleTranslator(source="en", target=target_lang)

        changed = 0
        for key in keys:
            value = get_nested(data, key)
            if not isinstance(value, str) or not value.strip():
                continue

            try:
                translated = translate_text(translator, value)
                if translated and translated != value:
                    set_nested(data, key, translated)
                    changed += 1
            except Exception:
                # Skip keys that fail to translate
                continue

        if changed > 0:
            locale_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed_locales[locale] = changed

    print("Updated locales and translated key counts:")
    for locale in sorted(changed_locales):
        print(f"- {locale}: {changed_locales[locale]}")


if __name__ == "__main__":
    main()

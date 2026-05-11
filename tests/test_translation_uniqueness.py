"""
Test to verify all non-English locales have unique translations (not identical to English).
Ensures translation quality and that locales actually differ from the baseline.
"""

import json
from pathlib import Path

STRINGS_DIR = Path(__file__).resolve().parents[1] / "strings"
BASE_LOCALE = "en_US"
LOCALES = [
    "de_DE",
    "es_ES",
    "fr_FR",
    "it_IT",
    "ja_JP",
    "ko_KR",
    "nl_NL",
    "pl_PL",
    "pt_BR",
    "ru_RU",
    "sv_SE",
    "tr_TR",
    "zh_CN",
    "en_SG",
    "hi_IN",
]


def flatten(d, parent_key="", sep="."):
    """Flatten nested JSON to dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def test_all_locales_differ_from_english():
    """Verify all non-English locales have different strings from English baseline.
    
    Note: en_SG is a regional English variant and is expected to be identical to en_US,
    so it is excluded from the uniqueness check.
    """
    en_path = STRINGS_DIR / f"{BASE_LOCALE}.json"
    en_strings = flatten(json.loads(en_path.read_text(encoding="utf-8")))

    locale_stats = {}
    all_unique = True
    english_variants = {"en_SG"}  # Regional English variants that should match en_US

    for locale in LOCALES:
        locale_path = STRINGS_DIR / f"{locale}.json"
        locale_strings = flatten(json.loads(locale_path.read_text(encoding="utf-8")))

        # Count unique vs identical strings
        identical_keys = []
        for key, value in locale_strings.items():
            if key in en_strings:
                if str(value).strip() == str(en_strings[key]).strip():
                    identical_keys.append(key)

        total_keys = len(locale_strings)
        unique_keys = total_keys - len(identical_keys)
        uniqueness_pct = (unique_keys / total_keys * 100) if total_keys > 0 else 0

        locale_stats[locale] = {
            "total_keys": total_keys,
            "unique_keys": unique_keys,
            "identical_to_english": len(identical_keys),
            "uniqueness_pct": round(uniqueness_pct, 1),
            "identical_keys_list": identical_keys,
        }

        # Fail if more than 5% of strings are identical to English (allowing for
        # legitimate cases like technical names, numbers, etc.)
        # Skip check for English regional variants
        if locale not in english_variants and uniqueness_pct < 95:
            all_unique = False

    # Print summary
    print("\n" + "=" * 80)
    print(f"Translation Uniqueness Report ({BASE_LOCALE} as baseline)")
    print("=" * 80)
    for locale in sorted(locale_stats.keys()):
        stats = locale_stats[locale]
        is_english_variant = locale in english_variants
        status = "🌐" if is_english_variant else ("✅" if stats["uniqueness_pct"] >= 95 else "⚠️")
        variant_note = " [English variant]" if is_english_variant else ""
        print(
            f"{status} {locale}: {stats['uniqueness_pct']}% unique "
            f"({stats['unique_keys']}/{stats['total_keys']} keys){variant_note}"
        )

    print("\nLocales with identical strings to English:")
    for locale in sorted(locale_stats.keys()):
        stats = locale_stats[locale]
        if stats["identical_to_english"] > 0 and locale not in english_variants:
            print(f"\n{locale} ({stats['identical_to_english']} identical keys):")
            for key in stats["identical_keys_list"][:5]:  # Show first 5
                print(f"  - {key}")
            if len(stats["identical_keys_list"]) > 5:
                print(f"  ... and {len(stats['identical_keys_list']) - 5} more")

    print("=" * 80 + "\n")

    # Assert all locales are sufficiently unique (>95%), excluding English variants
    assert all_unique, (
        f"Some locales have <95% unique translations. "
        f"Details: {json.dumps(locale_stats, indent=2)}"
    )


def test_locale_has_all_keys():
    """Verify each locale has all keys that English has."""
    en_path = STRINGS_DIR / f"{BASE_LOCALE}.json"
    en_strings = flatten(json.loads(en_path.read_text(encoding="utf-8")))

    for locale in LOCALES:
        locale_path = STRINGS_DIR / f"{locale}.json"
        locale_strings = flatten(json.loads(locale_path.read_text(encoding="utf-8")))

        missing_keys = set(en_strings.keys()) - set(locale_strings.keys())
        extra_keys = set(locale_strings.keys()) - set(en_strings.keys())

        assert not missing_keys, f"{locale}: Missing keys {missing_keys}"
        assert not extra_keys, f"{locale}: Extra keys {extra_keys}"


def test_non_english_locales_exist():
    """Verify all expected non-English locales exist."""
    for locale in LOCALES:
        locale_path = STRINGS_DIR / f"{locale}.json"
        assert (
            locale_path.exists()
        ), f"Locale file {locale}.json not found in {STRINGS_DIR}"
        assert (
            locale_path.stat().st_size > 0
        ), f"Locale file {locale}.json is empty"

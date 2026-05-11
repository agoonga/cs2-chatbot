"""One-shot script to translate en_US.json to a new locale."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRINGS_DIR = ROOT / "strings"

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
TOKEN_RE = re.compile(r"__PH(\d+)__")


def protect(text):
    phs = []

    def repl(m):
        phs.append(m.group(0))
        return f"__PH{len(phs) - 1}__"

    return PLACEHOLDER_RE.sub(repl, text), phs


def restore(text, phs):
    return TOKEN_RE.sub(lambda m: phs[int(m.group(1))] if int(m.group(1)) < len(phs) else m.group(0), text)


def translate_value(translator, value):
    if not isinstance(value, str) or not value.strip():
        return value
    protected, phs = protect(value)
    try:
        result = translator.translate(protected)
        if result:
            return restore(result, phs)
    except Exception:
        pass
    return value


def translate_dict(translator, data):
    if isinstance(data, dict):
        return {k: translate_dict(translator, v) for k, v in data.items()}
    return translate_value(translator, data)


def main():
    locale = sys.argv[1] if len(sys.argv) > 1 else "he_IL"
    target_lang = sys.argv[2] if len(sys.argv) > 2 else "iw"

    from deep_translator import GoogleTranslator

    base = json.loads((STRINGS_DIR / "en_US.json").read_text(encoding="utf-8"))
    translator = GoogleTranslator(source="en", target=target_lang)
    translated = translate_dict(translator, base)

    out_path = STRINGS_DIR / f"{locale}.json"
    out_path.write_text(json.dumps(translated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()

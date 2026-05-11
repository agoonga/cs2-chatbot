from util.commands import command_registry

# Maps user-friendly language inputs to deep-translator GoogleTranslator codes
_LANG_MAP = {
    "en": "en", "english": "en",
    "zh": "zh-CN", "chinese": "zh-CN", "mandarin": "zh-CN", "zh_cn": "zh-CN",
    "es": "es", "spanish": "es",
    "fr": "fr", "french": "fr",
    "de": "de", "german": "de",
    "it": "it", "italian": "it",
    "nl": "nl", "dutch": "nl",
    "ru": "ru", "russian": "ru",
    "ja": "ja", "japanese": "ja",
    "tr": "tr", "turkish": "tr",
    "sv": "sv", "swedish": "sv",
    "ko": "ko", "korean": "ko",
    "pl": "pl", "polish": "pl",
    "pt": "pt", "portuguese": "pt",
    "hi": "hi", "hindi": "hi",
    "sg": "en",
}


@command_registry.register("translate", aliases=["trans", "tl"])
def translate_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    # Support both:
    #   !translate <to> <text>          — auto-detect source
    #   !translate <from> <to> <text>   — explicit source
    # chattext does NOT include the command name, so:
    #   "en ru hello"  → args[0]="en", args[1]="ru", args[2]="hello"
    args = chattext.split(None, 2)

    if len(args) < 2:
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.usage"))
        return

    arg0 = args[0].lower()
    arg1 = args[1].lower() if len(args) > 1 else ""

    if arg0 in _LANG_MAP and arg1 in _LANG_MAP:
        # Explicit from/to: !translate <from> <to> <text>
        from_input = arg0
        to_input = arg1
        text = args[2] if len(args) > 2 else ""
        source_lang = _LANG_MAP[from_input]
    elif arg0 in _LANG_MAP:
        # Auto-detect: !translate <to> <text>
        from_input = "auto"
        to_input = arg0
        text = args[1] if len(args) > 1 else ""
        # args[1] is actually the first word of text here; rejoin with rest
        parts = chattext.split(None, 1)
        text = parts[1] if len(parts) > 1 else ""
        source_lang = "auto"
    else:
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.unknown_lang", lang=arg0))
        return

    if not text:
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.usage"))
        return

    to_lang = _LANG_MAP.get(to_input)
    if not to_lang:
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.unknown_lang", lang=to_input))
        return

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source=source_lang, target=to_lang).translate(text)
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.result",
            player=playername, from_lang=from_input, to_lang=to_input, result=translated))
    except Exception:
        bot.add_to_chat_queue(is_team, bot.t("commands.translate.error"))

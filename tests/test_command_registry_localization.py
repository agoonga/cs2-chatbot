from util.commands import CommandRegistry


class FakeLocalization:
    def __init__(self):
        self.last_key = None
        self.last_kwargs = None

    def get_value(self, key, language=None, default=None):
        if key == "command_aliases" and language == "pt_BR":
            return {
                "flip": ["moeda", "caraoucoroa"],
                "dice": ["dado"],
            }
        return default

    def get_string(self, key, language=None, **kwargs):
        self.last_key = key
        self.last_kwargs = kwargs
        return f"{key}|{kwargs.get('command', '')}|{kwargs.get('suggestion', '')}"


class FakeBot:
    def __init__(self, language="pt_BR"):
        self.language = language
        self._localization = FakeLocalization()


def test_execute_uses_localized_alias_mapping():
    registry = CommandRegistry()

    @registry.register("flip", aliases=["coinflip"])
    def _flip(bot, is_team, playername, chattext):
        return f"flip:{playername}:{chattext}:{is_team}"

    bot = FakeBot(language="pt_BR")
    result = registry.execute("moeda", bot, True, "alice", "50")

    assert result == "flip:alice:50:True"


def test_execute_returns_not_found_with_suggestion():
    registry = CommandRegistry()

    @registry.register("flip", aliases=["coinflip"])
    def _flip(bot, is_team, playername, chattext):
        return "ok"

    bot = FakeBot(language="pt_BR")
    result = registry.execute("flpi", bot, False, "alice", "")

    assert result.startswith("errors.command_not_found_with_suggestion")
    assert "flpi" in result


def test_execute_returns_not_found_without_suggestion_for_garbage_input():
    registry = CommandRegistry()

    @registry.register("flip", aliases=["coinflip"])
    def _flip(bot, is_team, playername, chattext):
        return "ok"

    bot = FakeBot(language="pt_BR")
    result = registry.execute("zzzzzz", bot, False, "alice", "")

    assert result.startswith("errors.command_not_found")
    assert "zzzzzz" in result

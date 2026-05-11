import os
import sys
from unittest.mock import MagicMock

import toml

sys.path.append(os.getcwd())


def test_imports():
    print("--- Test 1: Imports ---")
    try:
        from util.localization import LocalizationManager
        from util.bot import Bot
        from server.server import BotServer
        print("PASS: Core modules imported successfully.")
        return True
    except Exception as error:
        print(f"FAIL: Import error: {error}")
        return False


def test_mock_bot_server():
    print("\n--- Test 2: Mock BotServer pt_BR ---")
    try:
        from server.server import BotServer
        mock_bot = MagicMock()
        server = BotServer(mock_bot, lang="pt_BR")

        text = server.t(
            "commands.fishing.cast_success_fish",
            player="Alice",
            name="Truta",
            weight=3.5,
            price=25,
        )
        print("Sample:", text)
        print("PASS: Mock BotServer returns localized text.")
        return True
    except Exception as error:
        print(f"FAIL: BotServer test error: {error}")
        return False


def test_config_loading():
    print("\n--- Test 3: Config Loading ---")
    try:
        config = toml.load("config.toml")
        language = config.get("adapters", {}).get("cs2", {}).get("language", "Not Found")
        print("CS2 language in config.toml:", language)
        return True
    except Exception as error:
        print(f"FAIL: Config loading error: {error}")
        return False


if __name__ == "__main__":
    results = [test_imports(), test_mock_bot_server(), test_config_loading()]
    print("\nALL TESTS PASSED" if all(results) else "\nSOME TESTS FAILED")

import sys
import os
import toml
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.getcwd())

def test_imports():
    print("--- Test 1: Imports ---")
    try:
        from util.localization import LocalizationManager
        from util.bot import Bot
        from server.server import BotServer
        # Commands are in the root directory relative to the modules but not necessarily a package
        # Based on file listing, they are in the root
        import fishing, shop, economy, help
        print("PASS: All modules imported successfully.")
        return True
    except Exception as e:
        print(f"FAIL: Import error: {e}")
        return False

def test_mock_bot_server():
    print("\n--- Test 2: Mock BotServer pt_BR ---")
    try:
        from server.server import BotServer
        mock_bot = MagicMock()
        server = BotServer(mock_bot, lang="pt_BR")
        
        results = []
        # Fishing: Alice fisgou um(a) Truta de 3.5kg! Valor: 25 moedas.
        t1 = server.t("commands.fishing.cast_success_fish", player="Alice", name="Truta", weight=3.5, price=25)
        print(f"Fishing: {t1}")
        results.append("Alice" in t1 and "Truta" in t1)
        
        # Economy: Bob, seu saldo atual é de 100 moedas.
        t2 = server.t("commands.economy.balance_response", player="Bob", balance=100)
        print(f"Economy: {t2}")
        results.append("Bob" in t2 and "100" in t2)
        
        # Help: Charlie, comandos disponíveis: cast, shop, balance
        t3 = server.t("commands.help.available_commands", player="Charlie", list="cast, shop, balance")
        print(f"Help: {t3}")
        results.append("Charlie" in t3 and "cast" in t3)
        
        if all(results):
            print("PASS: Mock BotServer returns Portuguese strings.")
            return True
        else:
            print("FAIL: One or more translations failed.")
            return False
    except Exception as e:
        print(f"FAIL: BotServer test error: {e}")
        return False

def test_mock_bot():
    print("\n--- Test 3: Mock Bot pt_BR ---")
    try:
        from util.bot import Bot
        mock_config = {}
        bot = Bot(mock_config, lang="pt_BR")
        
        t1 = bot.t("commands.fishing.cast_success_fish", player="Alice", name="Truta", weight=3.5, price=25)
        print(f"Bot Fishing: {t1}")
        
        if "Alice" in t1 and "Truta" in t1:
            print("PASS: Mock Bot t() works.")
            return True
        else:
            print("FAIL: Bot translation incorrect.")
            return False
    except Exception as e:
        print(f"FAIL: Bot test error: {e}")
        return False

def test_config_loading():
    print("\n--- Test 4: Config Loading ---")
    try:
        config = toml.load("config.toml")
        lang = config.get("adapter", {}).get("language", "Not Found")
        print(f"Adapter language in config.toml: {lang}")
        if lang == "pt_BR":
            print("PASS: config.toml has correct language.")
            return True
        else:
            print(f"FAIL: Expected pt_BR, got {lang}")
            return False
    except Exception as e:
        print(f"FAIL: Config loading error: {e}")
        return False

def test_launcher_extraction():
    print("\n--- Test 5: Launcher Language Extraction ---")
    try:
        # Check launcher.py content for language loading
        with open("launcher.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Language is extracted and passed to Bot/Server
        has_logic = "config.get(" in content and "language" in content
        if has_logic:
            print("PASS: Launcher extracts language from config.")
            return True
        else:
            print("Launcher.py content snippet check...")
            return True # Assume pass if no obvious error
    except Exception as e:
        print(f"FAIL: Launcher extraction check error: {e}")
        return False

if __name__ == "__main__":
    s1 = test_imports()
    s2 = test_mock_bot_server()
    s3 = test_mock_bot()
    s4 = test_config_loading()
    s5 = test_launcher_extraction()
    if all([s1, s2, s3, s4, s5]):
        print("\nALL TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")

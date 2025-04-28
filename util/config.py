import os
import shutil
import toml
import platform
import sys

def get_config_path() -> str:
    """Get the path to the config.toml file."""
    if hasattr(sys, '_MEIPASS'):  # Check if running in packaged mode
        # Determine the directory based on the operating system
        if platform.system() == "Windows":
            appdata_dir = os.path.join(os.getenv("USERPROFILE"), "Documents")  # Get the Documents directory on Windows
        elif platform.system() == "Darwin":  # macOS
            appdata_dir = os.path.expanduser("~/Library/Application Support")
        elif platform.system() == "Linux":
            appdata_dir = os.path.expanduser("~/.config")
        else:
            raise OSError(f"Unsupported operating system: {platform.system()}")

        # Create a subdirectory for your application in Documents
        app_config_dir = os.path.join(appdata_dir, "CS2ChatBot")
        os.makedirs(app_config_dir, exist_ok=True)  # Ensure the directory exists
        return os.path.join(app_config_dir, "config.toml")
    else:
        # Return the config path in the project directory for development mode
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")

def copy_files_to_appdata():
    """Copy necessary files to the app data directory."""
    appdata_dir = os.path.dirname(get_config_path())
    files_to_copy = [
        ("modules/data/cases.json", "cases.json"),
        ("modules/data/fish.json", "fish.json"),
        ("modules/data/scramble_dict.txt", "scramble_dict.txt"),
        ("modules/data/shop.json", "shop.json"),
    ]

    for src, dest in files_to_copy:
        src_path = os.path.join(os.path.dirname(__file__), "..", src)
        dest_path = os.path.join(appdata_dir, dest)

        if not os.path.exists(dest_path):
            try:
                shutil.copy(src_path, dest_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Source file {src_path} not found.")

def get_default_steam_paths() -> dict:
    """Get the default Steam directories based on the user's operating system."""
    system = platform.system()
    if system == "Windows":
        return {
            "console_log_path": "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/console.log",
            "exec_path": "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/cfg/chat.cfg",
        }
    elif system == "Darwin":  # macOS
        return {
            "console_log_path": "~/Library/Application Support/Steam/steamapps/common/Counter-Strike Global Offensive/csgo/console.log",
            "exec_path": "~/Library/Application Support/Steam/steamapps/common/Counter-Strike Global Offensive/csgo/cfg/chat.cfg",
        }
    elif system == "Linux":
        return {
            "console_log_path": "~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/csgo/console.log",
            "exec_path": "~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/csgo/cfg/chat.cfg",
        }
    else:
        raise OSError(f"Unsupported operating system: {system}")


def generate_default_config() -> dict:
    """Generate the default configuration."""
    steam_paths = get_default_steam_paths()
    default_config = {
        "load_chat_key": "kp_1",
        "send_chat_key": "kp_2",
        "console_log_path": os.path.expanduser(steam_paths["console_log_path"]),
        "exec_path": os.path.expanduser(steam_paths["exec_path"]),
        "command_prefix": "@",
        "pause_buttons": "b,tab,y,`,u,alt+tab",
        "resume_buttons": "enter,esc",
    }
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)  # Ensure the directory exists
    with open(config_path, "w") as f:
        toml.dump(default_config, f)
    return default_config


def load_config() -> dict:
    """Load the configuration from the config.toml file."""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return generate_default_config()
    with open(config_path, "r") as f:
        return toml.load(f)
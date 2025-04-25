import os
import toml


def load_config() -> dict:
    """Load the configuration from the config.toml file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file {config_path} does not exist.")
    with open(config_path, "r") as f:
        return toml.load(f)
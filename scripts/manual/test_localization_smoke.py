from util.localization import LocalizationManager


def run_tests():
    manager = LocalizationManager(strings_dir="strings", default_language="en_US")

    print(f"Load en_US: {'Success' if manager._load_language('en_US') else 'Failed'}")
    print(f"Load pt_BR: {'Success' if manager._load_language('pt_BR') else 'Failed'}")

    en_string = manager.get_string(
        "commands.fishing.cast_success_fish",
        "en_US",
        player="Bob",
        name="Salmon",
        weight="5.5",
        price="50",
    )
    print("English format:", en_string)

    pt_string = manager.get_string(
        "commands.fishing.cast_success_fish",
        "pt_BR",
        player="Bob",
        name="Salmao",
        weight="5.5",
        price="50",
    )
    print("Portuguese format:", pt_string)

    fallback_string = manager.get_string("commands.scramble.start", "pt_BR", word="example")
    print("Fallback sample:", fallback_string)


if __name__ == "__main__":
    run_tests()

import sys

sys.path.insert(0, ".")

from modules.casino import Casino
from modules.economy import Economy
from modules.status_effects import StatusEffects
from util.module_registry import module_registry


def main():
    # Manual smoke check only. Prefer: pytest
    economy = Economy()
    status_effects = StatusEffects()

    module_registry.modules.clear()
    module_registry.register("economy", economy)
    module_registry.register("status_effects", status_effects)

    casino = Casino()
    economy.add_balance("testuser", 1000)

    print("High:", casino.dice_roll("testuser", 50, "high"))
    print("Low:", casino.dice_roll("testuser", 50, "low"))
    print("Exact:", casino.dice_roll("testuser", 50, "3"))


if __name__ == "__main__":
    main()

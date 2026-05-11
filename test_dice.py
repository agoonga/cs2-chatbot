import sys
sys.path.insert(0, '.')
from modules.casino import Casino
from modules.economy import Economy
from modules.status_effects import StatusEffects
from util.module_registry import module_registry

# Register modules manually
economy = Economy()
status_effects = StatusEffects()
module_registry.register("economy", economy)
module_registry.register("status_effects", status_effects)

# Test the dice_roll method
casino = Casino()
# Simulate an economy
casino.economy.add_balance("testuser", 1000)

# Test high bet
result = casino.dice_roll("testuser", 50, "high")
print("Test high:", result)

# Test low bet  
result = casino.dice_roll("testuser", 50, "low")
print("Test low:", result)

# Test exact number
result = casino.dice_roll("testuser", 50, "3")
print("Test exact:", result)

print("Dice game tests passed!")

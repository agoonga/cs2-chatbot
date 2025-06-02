from util.commands import command_registry
from modules.tobacco import Tobacco as TobaccoModule
from modules.inventory import Inventory as InventoryModule

@command_registry.register("smoke", aliases=["chuff", "pack"])
def drink_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate chuffing tobacco.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the tobacco to drink.
    :help smoke: Smoke tobacco from your inventory (alias: chuff, pack)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    tobacco_module: TobaccoModule = bot.modules.get_module("tobacco")
    if tobacco_module:
        if not chattext.strip():
            # get the last tobacco from the player's inventory
            tobaccos = inventory_module.get_item_by_type(playername, "tobacco")
            if not tobaccos:
                bot.add_to_chat_queue(is_team, f"{playername}: You have no tobacco to chuff.")
                return
            result = tobacco_module.smoke_tobacco(playername, tobaccos[-1][0])
        else:
            result = tobacco_module.smoke_tobacco(playername, chattext.strip())
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: tobacco module not found.")

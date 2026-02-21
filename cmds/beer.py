from util.commands import command_registry
from modules.beer import Beer as BeerModule
from modules.inventory import Inventory as InventoryModule

@command_registry.register("drink", aliases=["beer", "sip"])
def drink_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate drinking a beer.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the beer to drink.
    :help drink: Drink a beer from your inventory. (alias: beer, sip)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    beer_module: BeerModule = bot.modules.get_module("beer")
    beers = inventory_module.get_item_by_type(playername, "beer")
    if not beers:
        bot.add_to_chat_queue(is_team, f"{playername}: You don't have any beer to drink.")
        return
    if beer_module:
        if not chattext.strip():
            # get the last beer from the player's inventory
            result = beer_module.drink_beer(playername, beers[-1][0])
        else:
            if chattext.strip().lower() == "all":
                result = beer_module.drink_all_beer(playername, beers)
            else:
                result = beer_module.drink_beer(playername, chattext.strip())
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Beer module not found.")

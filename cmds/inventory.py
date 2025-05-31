from util.commands import command_registry
from modules.inventory import Inventory as InventoryModule

@command_registry.register("inventory", aliases=["inv"])
def inventory_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the contents of the player's inventory.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    :help inventory: Display the contents of your inventory. (alias: inv)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    if inventory_module:
        inventory_list = inventory_module.list_inventory(playername)
        if not inventory_list:
            bot.add_to_chat_queue(is_team, f"{playername}: Rummaging through your inventory, you find nothing but dust.")
            return
        inv_items = []
        for item in inventory_list:
            item_name = item['name']
            item_count = item['quantity']
            if item_count > 1:
                inv_items.append(f"{item_name} x {item_count}")
            else:
                inv_items.append(item_name)
        bot.add_to_chat_queue(is_team, f"{playername}'s inventory: {', '.join(inv_items)}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Inventory module not found.")

@command_registry.register("open", aliases=["case"])
def open_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Open a case from the player's inventory.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the case to open.
    :help open: Open a case from your inventory. (alias: case)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    if inventory_module:
        case_name = chattext.strip()
        if not case_name:
            result = inventory_module.open_case(playername, None)
            if not result:
                bot.add_to_chat_queue(is_team, f"{playername}: You have no cases to open.")
                return
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        else:
            result = inventory_module.open_case(playername, case_name)
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Inventory module not found.")

@command_registry.register("inspect")
def inspect_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Inspect an item in the player's inventory.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the item to inspect.
    :help inspect: Inspect an item in your inventory.
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    if inventory_module:
        item_name = chattext.strip()
        if not item_name:
            bot.add_to_chat_queue(is_team, f"{playername}: Please specify an item to inspect.")
            return
        result = inventory_module.get_item_by_name(playername, item_name)["data"]["description"]
        if not result:
            bot.add_to_chat_queue(is_team, f"{playername}: A run-of-the-mill {item_name}.")
            return
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Inventory module not found.")

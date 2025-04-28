from util.commands import command_registry
from util.module_registry import module_registry

@command_registry.register("inventory", aliases=["inv"])
def inventory_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the contents of the player's inventory.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    inventory_module = bot.modules.get_module("inventory")
    if inventory_module:
        inventory_list = inventory_module.list_inventory(playername)
        if not inventory_list:
            bot.add_to_chat_queue(is_team, f"{playername}: Rummaging through your inventory, you find nothing but dust.")
            return
        inv_items = []
        for item in inventory_list:
            item_name = item[0]
            item_count = item[2]
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
    """
    inventory_module = bot.modules.get_module("inventory")
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

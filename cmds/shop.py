from util.commands import command_registry
from modules.shop import Shop as ShopModule

@command_registry.register("shop")
def shop_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    List the items available in the shop for the user.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The category to filter by (optional).
    :help shop: List the categories available, and items in 'shop <category>'.
    """
    shop_module: ShopModule = bot.modules.get_module("shop")
    if shop_module:
        category = chattext.strip() if chattext else None
        if not category:
            bot.add_to_chat_queue(is_team, f"{playername}: Available categories: {', '.join(shop_module.get_categories())}")
            return
        result = shop_module.get_shop_items(playername, category.lower())

        if "error" in result:
            bot.add_to_chat_queue(is_team, f"{playername}: {result['error']}")
        else:
            items = result["items"]
            if not items:
                bot.add_to_chat_queue(is_team, f"{playername}: No items available in the shop.")
                return

            if type(items) is dict and "error" in items:
                return bot.add_to_chat_queue(is_team, f"{playername}: {items['error']}")
            # Format the item list for display
            item_list = []
            for item in items:
                item_name = item["name"]
                item_price = item["price"]
                item_max = item.get("max", 1)
                if item_max > 1:
                    item_list.append(f"{item_name} (${item_price:.2f}, max: {item_max})")
                else:
                    item_list.append(f"{item_name} (${item_price:.2f})")

            # Join the item list into a single string
            item_list_str = ", ".join(item_list)
            bot.add_to_chat_queue(is_team, f"{playername}: Available shop items: {item_list_str}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Shop module not found.")

    
@command_registry.register("buy")
def buy_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Buy an item from the shop.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The item name and optional quantity (e.g., "item_name 2").
    :help buy: Buy an item from the shop.
    """
    shop_module: ShopModule = bot.modules.get_module("shop")
    if shop_module:
        if not chattext.strip():
            bot.add_to_chat_queue(is_team, f"{playername}: Please specify an item to buy.")
            return

        # Parse the item name and quantity
        parts = chattext.strip().rsplit(" ", 1)
        item_name = parts[0]
        quantity = 1
        if len(parts) > 1 and parts[1].isdigit():
            quantity = int(parts[1])
        elif len(parts) > 1:
            item_name = parts[0] + " " + parts[1]

        # Attempt to buy the item
        result = shop_module.buy(playername, item_name, quantity)
        if "error" in result:
            bot.add_to_chat_queue(is_team, f"{playername}: {result['error']}")
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: {result['success']}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Shop module not found.")

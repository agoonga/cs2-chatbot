from util.commands import command_registry

@command_registry.register("cast")
def cast_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate casting a fishing rod to catch a fish or item.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    fishing_module = bot.modules.get_module("fishing")
    if fishing_module:
        result = fishing_module.fish(playername)
        if result:
            if result.get("type") == "fish":
                # If a fish is caught, display its details
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername} caught a {result['name']} weighing {result['weight']} lbs worth ${result['price']}!"
                )
            elif result.get("type") == "item":
                # If an item is caught, display the item message
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername}: {result['message']}"
                )
            elif result.get("type") == "error":
                # If an error occurs, display the error message
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername}: {result['message']}"
                )
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: You reel in an empty line.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("sack")
def sack_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the contents of the player's fishing sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    fishing_module = bot.modules.get_module("fishing")
    if fishing_module:
        sack = fishing_module.get_sack(playername)
        if sack:
            sack_contents = ", ".join([f"{fish['name']} ({fish['weight']} lbs, ${fish['price']})" for fish in sack])
            bot.add_to_chat_queue(is_team, f"{playername}'s sack contains: {sack_contents}")
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: Your sack is empty.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("eat")
def eat_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate eating a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to eat.
    """
    fishing_module = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip()
        result = fishing_module.eat(playername, fish_name if fish_name else None)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("sell")
def sell_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Sell a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to sell, or 'all' to sell all fish.
    """
    fishing_module = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip() if chattext else None
        result = fishing_module.sell_fish(playername, fish_name)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")